#!/usr/bin/python

import subprocess
import sys
import re


def get_all_nspaces():
    p = subprocess.Popen(
        ['sudo', 'ip', 'netns'], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.strip().split("\n")


def show_nspace(ns):
    cmd = ['sudo', 'ip', 'netns', 'exec', ns, 'ip', 'addr']
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out


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
    pattern = "192.168.199.(25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|[2-9])/24"
    if len(sys.argv) >= 2:
        pattern = sys.argv[1]
    print("the namspace that %s belongs to" % pattern)
    print("*" * 80)
    print(find_namespaces(pattern))
