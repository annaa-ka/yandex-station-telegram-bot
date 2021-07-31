from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange
from typing import Callable, Optional, Dict
import ipaddress

class YandexIOListener:
    add_handlerer = None
    browser = None

    def start(self, handlerer: Callable, zeroconf: Zeroconf):
        self.add_handlerer = handlerer
        self.browser = ServiceBrowser(zeroconf, '_yandexio._tcp.local.',
                                      handlers=[self._zeroconf_handler])

    def stop(self, *args):
        self.browser.cancel()
        self.browser.zc.close()

    def _zeroconf_handler(self, zeroconf: Zeroconf, service_type: str,
                          name: str, state_change: ServiceStateChange):
        info = zeroconf.get_service_info(service_type, name)
        if not info or len(info.addresses) == 0:
            return

        properties = {
            k.decode(): v.decode() if isinstance(v, bytes) else v
            for k, v in info.properties.items()
        }

        self.add_handlerer({
            'device_id': properties['deviceId'],
            'platform': properties['platform'],
            'host': str(ipaddress.ip_address(info.addresses[0])),
            'port': info.port
        })


def found_local_speaker(info: dict):
    print(info)


if __name__ == "__main__":

    zeroconf = Zeroconf()

    listener = YandexIOListener()
    listener.start(found_local_speaker, zeroconf)

    try:
        input("Press enter to exit...\n\n")
    finally:
        zeroconf.close()