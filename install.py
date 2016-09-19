# Installer for WeeWx EveryAware extension

from setup import ExtensionInstaller


def loader():
    return EveryAwareInstaller()


class EveryAwareInstaller(ExtensionInstaller):
    def __init__(self):
        super(EveryAwareInstaller, self).__init__(
                version="0.1",
                name='everyaware',
                description='Upload weather data to EveryAware.',
                author='Michael Steininger',
                author_email='steininger-michael@web.de',
                restful_services='user.weewx-everyaware.EveryAware',
                config={
                    'StdRESTful': {
                        'EveryAware': {
                            'feeds': 'replace_me'}}},
                files=[('bin/user', ['bin/user/weewx-everyaware.py'])]
        )
