#!/usr/bin/env python

# Copyright (c) 2016 Michael Steininger <steininger-michael@web.de>

import Queue
import re
import sys
import syslog
import time
import json
import urllib2

# getnode from uuid usually returns the mac address as a 48 bit integer.
# Although it can also fake the mac address with a random 48 bit integer.
# see: http://stackoverflow.com/questions/159137/getting-mac-address
from uuid import getnode as get_mac

import weewx
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool, accumulateLeaves

VERSION = 0.1

def logmsg(level, msg):
    syslog.syslog(level, 'restx: EveryAware: %s' % msg)


def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)


def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)


def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)


class EveryAware(weewx.restx.StdRESTbase):

    def __init__(self, engine, config_dict):
        super(EveryAware, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)
        try:
            site_dict = config_dict['StdRESTful']['EveryAware']
            site_dict = accumulateLeaves(site_dict, max_level=1)
            site_dict['feeds']
            site_dict['geoLatitude'] = config_dict['Station']['latitude']
            site_dict['geoLongitude'] = config_dict['Station']['longitude']
            site_dict['location'] = config_dict['Station']['location']
            site_dict['altitude'] = config_dict['Station']['altitude']
            site_dict['stationType'] = config_dict['Station']['station_type']
        except KeyError, e:
            logerr("Data will not be posted: Missing option %s" % e)
            return
        site_dict['manager_dict'] = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'wx_binding')

        self.archive_queue = Queue.Queue()
        self.archive_thread = EveryAwareThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        loginf('Data will be uploaded')

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class EveryAwareThread(weewx.restx.RESTThread):
    _API_URL = 'http://cs.everyaware.eu/api/v1/packets'
    _DATA_MAP = {'out_temp': ('outTemp', '%.1f'),  # C
                 'in_temp': ('inTemp', '%.1f'), # C
                 'dew_point': ('dewpoint', '%.1f'), # C
                 'heat_index': ('heatindex', '%.1f'), # C
                 'wind_chill': ('windchill', '%.1f'),  # C
                 'wind_avg': ('windSpeed', '%.1f'),  # m/s
                 'wind_direction': ('windDir', '%.0f'),  # degree
                 'wind_max': ('windGust', '%.1f'),  # m/s
                 'wind_max_direction': ('windGustDir', '%.0f'), # degree
                 'air_pressure': ('barometer', '%.3f'),  # hPa
                 'in_humidity': ('inHumidity', '%.1f'),  # %
                 'out_humidity': ('outHumidity', '%.1f'),  # %
                 'rain': ('rain', '%.2f'),  # mm
                 'rain_rate': ('rainRate', '%.2f'), # mm/hr
                 'interval': ('interval', '%d'),  # seconds
                 'precip_interval': ('interval', '%d')  # seconds
                 }

    def __init__(self, queue, feeds, geoLatitude, geoLongitude, location,
                 altitude, stationType, manager_dict,
                 sourceId = get_mac(), contentDetailsType='generic',
                 server_url=_API_URL, skip_upload=False, post_interval=60,
                 max_backlog=sys.maxint, stale=None, log_success=True,
                 log_failure=True, timeout=60, max_tries=3, retry_wait=5):
        super(EveryAwareThread, self).__init__(queue,
                                               protocol_name='EveryAware',
                                               manager_dict=manager_dict,
                                               post_interval=post_interval,
                                               max_backlog=max_backlog,
                                               stale=stale,
                                               log_success=log_success,
                                               log_failure=log_failure,
                                               max_tries=max_tries,
                                               timeout=timeout,
                                               retry_wait=retry_wait)
        self.feeds = feeds
        self.sourceId = sourceId
        self.contentDetailsType = contentDetailsType
        self.geoLatitude = geoLatitude
        self.geoLongitude = geoLongitude
        self.location = location
        self.altitude = altitude
        self.stationType = stationType
        self.server_url = server_url
        self.skip_upload = to_bool(skip_upload)

    def process_record(self, record, dbm):
        r = self.get_record(record, dbm)
        data = self.build_body(r)
        if self.skip_upload:
            raise weewx.restx.FailedPost("Upload disabled for this service")
        req = urllib2.Request(self.server_url, data, {'Content-Type': 'application/json'})
        req.add_header('User-Agent', "weewx/%s" % weewx.__version__)
        req.add_header('meta.feeds', self.feeds)
        req.add_header('meta.sourceId', self.sourceId)
        req.add_header('data.contentDetails.type', self.contentDetailsType)
        self.post_with_retries(req)

    def check_response(self, response):
        lines = []
        for line in response:
            lines.append(line)
        msg = ''.join(lines)
        if 'errorId' in response:
            raise weewx.restx.FailedPost("Server response: %s" % msg)

    def build_body(self, in_record):
        # put everything into the right units and scaling
        record = weewx.units.to_METRICWX(in_record)
        # put data into expected structure and format
        channels = {}
        for key in self._DATA_MAP:
            rkey = self._DATA_MAP[key][0]
            if record.has_key(rkey) and record[rkey] is not None:
                channels[key] = {'value': self._DATA_MAP[key][1] % record[rkey]}

        # add channel with general information
        channels['info'] = {
            'location': self.location,
            'altitude': self.altitude[0] + ' ' + self.altitude[1],
            'station_type': self.stationType
        }

        # add channel with geo information
        channels['geo'] = {
            'latitude': self.geoLatitude,
            'longitude': self.geoLongitude
        }

        json_data = json.dumps(
            [{
                'timestamp': int(record['dateTime'])*1000, # convert to ms
                'channels': channels
            }])
        loginf('json_data: %s' % json_data)
        if weewx.debug >= 1:
            logdbg('json_data: %s' % json_data)
        return json_data
