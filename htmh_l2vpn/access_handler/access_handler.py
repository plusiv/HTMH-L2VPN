from htmh_l2vpn.access_switch.access_switch import AccessSw
from htmh_l2vpn.mongodb.mongo_driver import NetworkAnatomy, HTMHDevice

from htmh_l2vpn.onos.onos import ONOSDriver

from itertools import combinations



class AccessHandler:
    def __init__(self):
        self.na = NetworkAnatomy()
        self.access_devices = self.na.access_devices_ids
        self.switches_id = {'of:0000c27e34dffd4f', 'of:0000068f79daf149',
                            'of:00006a2f1bc24a4c', 'of:0000823c3afb9d4c',
                            'of:000096510082cc4f'}

        self.onos_driver = ONOSDriver()

        self.access_sw = dict([(sw_id, AccessSw(id=sw_id, public_mac=self.onos_driver.get_sw_public_mac(sw_id)))
                          for sw_id in self.switches_id])

    def set_normal_functions(self):
        # Install internal fwd flows and arp
        for sw in self.access_devices:
            device = HTMHDevice(device_id=sw)
            hosts = device.hosts
            if len(hosts) > 1:
                self.onos_driver.install_arp_flow(device_id=device.of_id, hosts=device.hosts,
                                                  ports=device.active_ports)
                for pair in device.pairs_mac:
                    self.onos_driver.install_intents(macs_pair=pair)

    @staticmethod
    def device_normal_functions(device_id):
        device = HTMHDevice(device_id=device_id)

        hosts = device.hosts
        if len(hosts) > 1:
            ONOSDriver().install_arp_flow(device_id=device.of_id, hosts=device.hosts, ports=device.active_ports)
            for pair in device.pairs_mac:
                ONOSDriver().install_intents(macs_pair=pair)

    def create_l2vpn(self, devices: list, service_token: str):
        devices_pair = combinations(devices, 2)

        for index, device in enumerate(devices, start=1):
            self.access_sw[device].map_ips(index)

        for pair in devices_pair:
            device_a, device_b = pair
            self.access_sw[device_a].add_foreign_hosts(hosts=self.access_sw[device_b].hosts,
                                                       src_device_mac=self.access_sw[device_b].public_mac)
            self.access_sw[device_b].add_foreign_hosts(hosts=self.access_sw[device_a].hosts,
                                                       src_device_mac=self.access_sw[device_a].public_mac)

            self.onos_driver.install_incoming_flows(device=device_a,
                                                    hosts=self.access_sw[device_a].hosts,
                                                    service_token=service_token)
            self.onos_driver.install_incoming_flows(device=device_b,
                                                    hosts=self.access_sw[device_b].hosts,
                                                    service_token=service_token)

            self.onos_driver.install_outgoing_flows(device=device_a,
                                                    hosts=self.access_sw[device_a].hosts,
                                                    foreign_hosts=self.access_sw[device_a].foreign_hosts,
                                                    service_token=service_token)
            self.onos_driver.install_outgoing_flows(device=device_b,
                                                    hosts=self.access_sw[device_b].hosts,
                                                    foreign_hosts=self.access_sw[device_b].foreign_hosts,
                                                    service_token=service_token)

            self.onos_driver.install_shortest_path(src=device_a,
                                                   dst=device_b,
                                                   dst_public_mac=self.access_sw[device_b].public_mac,
                                                   service_token=service_token)
            self.onos_driver.install_shortest_path(src=device_b,
                                                   dst=device_a,
                                                   dst_public_mac=self.access_sw[device_a].public_mac,
                                                   service_token=service_token)

            for device in devices:
                self.onos_driver.install_arp_flow(device_id=device, hosts=self.access_sw[device].all_hosts,
                                                  ports=self.access_sw[device].active_ports)

    def delete_l2vpn(self, devices, service_token):
        self.onos_driver.delete_flow_app('l2vpn.core.path.' + service_token)
        self.onos_driver.delete_flow_app('l2vpn.outgoing.map.' + service_token)
        self.onos_driver.delete_flow_app('l2vpn.incoming.map.' + service_token)

        for device in devices:
            self.access_sw[device].wipe_foreign_hosts()
            if len(device) > 1:
                self.onos_driver.install_arp_flow(device_id=self.access_sw[device].device_id,
                                                  hosts=self.access_sw[device].hosts,
                                                  ports=self.access_sw[device].active_ports)

    def remote_default_gw(self, devices, service_token):
        pass
