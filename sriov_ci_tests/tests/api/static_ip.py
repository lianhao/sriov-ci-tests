# Copyright 2020 Intel Corporation
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

import re
import subprocess
import sys


def get_all_nspaces():
    p = subprocess.Popen(
        ['sudo', 'ip', 'netns'], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.strip().decode().split("\n")


def show_nspace(ns):
    cmd = ['sudo', 'ip', 'netns', 'exec', ns, 'ip', 'addr']
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode()


def shell_command(cmd):
    # cmd = ['sudo', 'ip', 'netns', 'exec', ns, 'ssh', "%s@%s" %(name, ip),
    # "'%s;ifconfig eth1 %s/24'" % (name ip)]
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out


def find_namespace(pattern):
    regex = re.compile(pattern)
    for ns in get_all_nspaces():
        out = show_nspace(ns)
        if regex.findall(out, re.MULTILINE):
            return ns


def find_namespaces(pattern):
    nss = []
    regex = re.compile(pattern)
    for ns in get_all_nspaces():
        out = show_nspace(ns)
        if regex.findall(out, re.MULTILINE):
            print(ns + "      ------------")
            print(out)
            print("*" * 80)
            nss.append(ns)
    return "\n".join(nss)


if __name__ == "__main__":
    pattern = r'192.168.199.'
    pattern += r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|[2-9])/24'
    if len(sys.argv) >= 2:
        pattern = sys.argv[1]
    print("the namspace that %s belongs to" % pattern)
    print("*" * 80)
    print(find_namespaces(pattern))
