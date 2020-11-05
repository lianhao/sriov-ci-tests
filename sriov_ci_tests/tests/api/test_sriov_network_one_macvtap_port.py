# Copyright 2014 IBM Corp.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import netaddr
import ipaddress
import functools
import six
import time

#from tempest.pci import pci
import pci

from tempest import config
from tempest import test
from tempest.lib.exceptions import SSHExecCommandFailed
from network_base import ExtendNetworkScenarioTest
import network_base as nb
from tempest.lib.common.utils import data_utils
from tempest.common.utils.linux import remote_client
from oslo_log import log as logging
from static_ip import shell_command

#Not stable
from tempest.scenario import manager
from tempest.common import waiters

CONF = config.CONF
LOG = logging.getLogger(__name__)

PRIVATE_IP_PATTERN = "192.168.198.(25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|[2-9])/24"
IFACEPATH = "/opt/stack/tempest/interface"

#hard code
PEER_HOST = os.getenv('PEER_HOST')
PEER_NAME = os.getenv('PEER_NAME')
PEER_PWD = os.getenv('PEER_PWD')

VM_PASSWD = 'cubswin:)'

PRIVATE_CIDR = "192.168.198.0/24"
PRIVATE_IP_START = "192.168.198.128"
PRIVATE_IP_END = "192.168.198.254"
PRIVATE_FIX_IP = "192.168.198.125"

SRIOV_IP_START = os.getenv('VM_INTERFACE_RANGE_START')
SRIOV_IPADDR_START = ipaddress.IPv4Address(unicode(SRIOV_IP_START))
SRIOV_CIDR = str(SRIOV_IPADDR_START).rsplit(".",1)[0] + ".0/24"
SRIOV_IP_END = str(SRIOV_IPADDR_START + 10)
SRIOV_FIX_IP = str(SRIOV_IPADDR_START + 5)

class TestNetworkAdvancedServerOps(ExtendNetworkScenarioTest):

    """
    This test case checks VM connectivity after some advanced
    instance operations executed:

     * Stop/Start an instance
     * Reboot an instance
     * Rebuild an instance
     * Pause/Unpause an instance
     * Suspend/Resume an instance
     * Resize an instance
    """

    @classmethod
    def check_preconditions(cls):
        super(TestNetworkAdvancedServerOps, cls).check_preconditions()
        if not (CONF.network.tenant_networks_reachable
                or CONF.network.public_network_id):
            msg = ('Either tenant_networks_reachable must be "true", or '
                   'public_network_id must be defined.')
            raise cls.skipException(msg)

    def _check_network_connectivity(self, should_connect=True):
        username = "cirros"
        private_key = self.keypair['private_key']
        self._check_tenant_network_connectivity(
            self.server, username, private_key,
            should_connect=should_connect,
            servers_for_debug=[self.server])

        print(self.sriov_ip)
        for i in range(60):
            print("%sth times to ping" % i)
            error = False
            try:
                linux_client = remote_client.RemoteClient(
                    PEER_HOST, PEER_NAME, PEER_PWD)
                linux_client.ping_host(self.sriov_ip)
            except Exception as e:
                # we only tolerance 20 times failed.
                error = True
                if i > 20:
                    raise Exception("Error: can not connect the instance "
                                    "by the sriov port!")
                else:
                    print(e)
            if not error:
                print("ping sriov port success!")
                break
            time.sleep(2)

    def _setup_network_and_servers(self):
        self.keypair = self.create_keypair()
        kwargs = {"name": "private"}
        private_network = self.create_network(**kwargs)
        cidr = netaddr.IPNetwork(PRIVATE_CIDR)
        ranges = {"start": PRIVATE_IP_START, "end": PRIVATE_IP_END}
        subnet = self.create_subnet(
            private_network, cidr=cidr,
            allocation_pools=[ranges], enable_dhcp=True)
        self.private_gateway = subnet["gateway_ip"]
        kwargs = {"binding:vnic_type": "normal",
                  "fixed_ips": [{"subnet_id": subnet['id'],
                                "ip_address": PRIVATE_FIX_IP}]}
        private_port = self.create_port(
            private_network, name="port-sriov", **kwargs)
        port_info = self.ports_client.show_port(private_port['id'])
        self.private_ip = port_info['port']['fixed_ips'][0]['ip_address']

        print(self.private_ip)
        kwargs = {"provider:network_type": "vlan",
                  "provider:physical_network": "physnet1",
                  "provider:segmentation_id": "1000"}

        sriov_network = self.create_network(**kwargs)
        cidr = netaddr.IPNetwork(SRIOV_CIDR)
        ranges = {"start": SRIOV_IP_START, "end": SRIOV_IP_END}
        subnet = self.create_subnet(
            sriov_network, cidr=cidr,
            allocation_pools=[ranges], enable_dhcp=False)
        kwargs = {"binding:vnic_type": "macvtap",
                  "fixed_ips": [{"subnet_id": subnet['id'],
                                "ip_address": SRIOV_IP_START}]}
        sriov_port = self.create_port(
            sriov_network, name="port-sriov-", **kwargs)
        port_info = self.ports_client.show_port(sriov_port['id'])
        self.sriov_ip = port_info['port']['fixed_ips'][0]['ip_address']
        self.sriov_port_id = sriov_port['id']

        cont = pci.gen_rc_local_dict(pci.INTERFACES)
        print(cont)
        personality = [
            {'path': "/etc/network/interfaces",
             'contents': cont}]

        create_kwargs = {
           'networks': [
               {'uuid': private_network["id"],'port': private_port['id']},
               {'uuid': sriov_network['id'], 'port': sriov_port['id']},
            ],
            'key_name': self.keypair['name'],
            'config_drive': True,
        }

        server_name = data_utils.rand_name('server-sriov')
        print(create_kwargs['networks'])

        server = self.servers_client.create_server(name=server_name,
                                         imageRef=CONF.compute.image_ref,
                                         flavorRef=CONF.compute.flavor_ref,
                                         # user_data=user_data,
                                         personality=personality,
                                         **create_kwargs)
        self.server = server['server']

        self.addCleanup(
            self.servers_client.delete_server, self.server['id'])
        waiters.wait_for_server_status(
             self.servers_client, self.server["id"], 'ACTIVE')

    @test.services('compute', 'network')
    def test_sriov_one_macvtap_port(self):
        self._setup_network_and_servers()
        time.sleep(30)
        port_info = self.ports_client.show_port(self.sriov_port_id)
        self.assertEqual('ACTIVE', port_info['port']['status'])
