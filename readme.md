WeeWX EveryAware
=
This is an extension for [WeeWX](https://github.com/weewx) that publishes data to [EveryAware](http://www.everyaware.eu).

# Installation

1. Download WeeWX EveryAware from https://github.com/SteiMi/weewx-everyaware/archive/master.tar.gz using:
```
wget -O weewx-everyaware.tar.gz https://github.com/SteiMi/weewx-everyaware/archive/master.tar.gz
```

2. Install the extension using:
```
wee_extension --install weewx-everyaware.tar.gz
```

3. Configure to which feeds the data should be uploaded by editing weewx.conf:
```
[StdRESTful]
        [[EveryAware]]
              feeds = replace_me
```
You can upload to multiple feeds at once by adding several feed id's to the config file separated by commas (e.g. feeds = feed1,feed2 if you want to upload data to feed1 and feed2).

4. Restart WeeWX
```
sudo /etc/init.d/weewx restart
```

# Notes
- This plugin currently only supports uploading data to feeds that have public write enabled
- Your MAC address will be used as source id as an integer when uploading
