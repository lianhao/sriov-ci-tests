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

import functools
import six
import base64
import netaddr

from tempest import config
from tempest import test
from tempest.lib.common.utils import test_utils
from tempest.lib.common.utils import data_utils
from oslo_log import log as logging
from oslo_utils import encodeutils

#Not stable
from tempest.scenario import manager

# original: from tempest import exceptions
# mine: from tempest.lib import exceptions
#from tempest import exceptions
from tempest.lib import exceptions

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ExtendNetworkScenarioTest(manager.NetworkScenarioTest):


    @classmethod
    def resource_setup(cls):
        super(ExtendNetworkScenarioTest, cls).resource_setup()
        cls.flavors_client = cls.os_primary.flavors_client
        cls.floating_ips_client = cls.os_primary.floating_ips_client
        # Glance image client v1
        cls.image_client = cls.os_primary.image_client
        # Compute image client
        cls.images_client = cls.os_primary.compute_images_client
        cls.keypairs_client = cls.os_primary.keypairs_client
        #cls.networks_client = cls.os_primary.networks_client
        # Nova security groups client
        cls.security_groups_client = cls.os_primary.security_groups_client
        cls.servers_client = cls.os_primary.servers_client
        cls.volumes_client = cls.os_primary.volumes_client_latest
        cls.snapshots_client = cls.os_primary.snapshots_client_latest
        cls.interface_client = cls.os_primary.interfaces_client
        # Neutron network client
        # cls.network_client = cls.os_primary.network_client
        # cls.network_client = cls.os_primary.networks_client
        # Neutron network client
        # cls.network_client = cls.os_primary.network_client
        # cls.networks_client = cls.os_primary.compute_networks_client
        cls.networks_client = cls.os_primary.networks_client
        cls.ports_client = cls.os_primary.ports_client
        cls.subnets_client = cls.os_primary.subnets_client
        # Heat client
        #cls.orchestration_client = cls.os_primary.orchestration_client

    def create_network(self, client=None, tenant_id=None,
                       namestart='network-sriov-', **kwargs):

        routers_client = None;

        if not client:
            client = self.networks_client

        if not routers_client:
            routers_client = self.routers_client

        if not tenant_id:
             tenant_id = client.tenant_id
        print("### tenentid:", tenant_id)
        if "name" in kwargs:
            name = kwargs["name"]
            kwargs.pop("name")
        else:
            name = data_utils.rand_name(namestart)

        result = client.create_network(
            name=name, tenant_id=tenant_id, **kwargs)

        #self.network = self._create_network(tenant_id=tenant_id, **kwargs)

        #self.network = net_resources.DeletableNetwork(
        #    networks_client=client,  routers_client=routers_client,
        #    **result['network'])
        network = result['network']
        self.assertEqual(network['name'], name)
        #self.addCleanup(self.delete_wrapper, self.network.delete)
        self.addCleanup(self.networks_client.delete_network, network['id'])
        return network

    def create_subnet(self, network, client=None,
                      namestart='subnet-smoke', **kwargs):
        if not client:
            client = self.subnets_client

        def cidr_in_use(cidr, tenant_id):
            """
            :return True if subnet with cidr already exist in tenant
                False else
            """
            cidr_in_use = self._list_subnets(tenant_id=tenant_id, cidr=cidr)
            return len(cidr_in_use) != 0

        ip_version = kwargs.pop('ip_version', 4)

        if ip_version == 6:
            netaddr.IPNetwork(
                CONF.network.project_network_v6_cidr)
            CONF.network.project_network_v6_mask_bits
        else:
            netaddr.IPNetwork(CONF.network.project_network_cidr)
            CONF.network.project_network_mask_bits

        result = None
        # Repeatedly attempt subnet creation with sequential cidr
        # blocks until an unallocated block is found.
        kwargs['cidr'] = str(kwargs['cidr'])
        str_cidr = kwargs['cidr']
        subnet = dict(
            name=data_utils.rand_name(namestart),
            network_id=network['id'],
            tenant_id=network['tenant_id'],
            ip_version=ip_version,
            **kwargs
        )
        try:
            result = client.create_subnet(**subnet)
        except exceptions.Conflict as e:
            is_overlapping_cidr = 'overlaps with another subnet' in str(e)
            if not is_overlapping_cidr:
                raise

        self.assertIsNotNone(result, 'Unable to allocate tenant network')
        #subnet = net_resources.DeletableSubnet(subnets_client=client,
        #                                       **result['subnet'])
        subnet = result['subnet']
        self.assertEqual(subnet['cidr'], str_cidr)
        #self.addCleanup(test_utils.call_and_ignore_notfound_exc,
        #                subnets_client.delete_subnet, subnet['id'])
        self.addCleanup(self.subnets_client.delete_subnet, subnet['id'])
        return subnet

    def create_port(self, network, client=None,
                    namestart='port-sriov-', **kwargs):

        if not client:
            client = self.ports_client

        name = data_utils.rand_name(namestart)
        if "name" in kwargs:
            name = kwargs["name"]
            kwargs.pop("name")
        result = client.create_port(
            name=name,
            network_id=network["id"],
            tenant_id=network["tenant_id"],
            **kwargs)
        self.assertIsNotNone(result, 'Unable to allocate port')
        #port = net_resources.DeletablePort(ports_client=client,
        #                                   **result['port'])
        #self.addCleanup(self.delete_wrapper, port.delete)
        port = result['port']
        self.addCleanup(self.ports_client.delete_port, port['id'])
        return port

    def father(self):
        return super(ExtendNetworkScenarioTest, self)


PCIINFO_DELIMITER = "*" * 40 + "%s" + "*" * 40
PCIINFO_DELIMITER_BEGIN = PCIINFO_DELIMITER % "PCI INFO BEGIN"
PCIINFO_DELIMITER_END = PCIINFO_DELIMITER % "PCI INFO END"


USER_DATA = ['#!/bin/sh -e',
             '# umount /mnt/',
             'exit 0']

CONSOLE_DATA = ['#!/bin/sh -e',
                'sudo echo "%s"' % PCIINFO_DELIMITER_BEGIN,
                'sudo lspci',
                'sudo echo "%s"'  % PCIINFO_DELIMITER_END,
                'exit 0']


def gen_user_data(userdata=USER_DATA):
    if hasattr(userdata, 'read'):
        userdata = userdata.read()
    # NOTE(melwitt): Text file data is converted to bytes prior to
    # base64 encoding. The utf-8 encoding will fail for binary files.
    if six.PY3:
        try:
            userdata = userdata.encode("utf-8")
        except AttributeError:
            # In python 3, 'bytes' object has no attribute 'encode'
            pass
    else:
        try:
            userdata = encodeutils.safe_encode(userdata)
        except UnicodeDecodeError:
            pass

    userdata_b64 = base64.b64encode(userdata).decode('utf-8')
    return userdata_b64


def get_pci_output(get_console_output, server_id):
    output = get_console_output(server_id)['output']
    lines = output.split('\n')
    if (len(lines) > 0 and lines.count(PCIINFO_DELIMITER_BEGIN) > 0
        and lines.count(PCIINFO_DELIMITER_END)):
        begin = lines.index(PCIINFO_DELIMITER_BEGIN) + 1
        end = lines.index(PCIINFO_DELIMITER_END)
        return lines[begin : end]


def retry_get_pci_output(get_console_output, server_id, retry=20):
    while retry > 0:
        out = get_pci_output(get_console_output, server_id)
        if out is None:
            retry = retry - 1
            time.sleep(1)
        else:
            return out
    raise Exception("Can't get the pci.info from VM!")
