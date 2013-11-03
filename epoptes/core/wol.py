#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Wake on LAN.
#
# Copyright (C) 2010-2013 Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FINESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import array
import fcntl
import socket
import struct
import sys


IFNAMSIZ = 16               # interface name size
# From <bits/ioctls.h>
SIOCGIFADDR = 0x8915        # get PA address
SIOCGIFBRDADDR  = 0x8919    # get broadcast PA address
SIOCGIFCONF = 0x8912        # get iface list


# create a socket to communicate with system
sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _call(ifname, func, ip = None):

    if ip is None:
        data = (ifname + '\0'*32)[:32]
    else:
        ifreq = (ifname + '\0' * IFNAMSIZ)[:IFNAMSIZ]
        data = struct.pack("16si4s10x", ifreq, socket.AF_INET, socket.inet_aton(ip))

    try:
        result = fcntl.ioctl(sockfd.fileno(), func, data)
    except IOError:
        return None

    return result


def getInterfaceList():
    """ Get all interface names in a list """
    # get interface list
    buffer = array.array('c', '\0' * 1024)
    ifconf = struct.pack("iP", buffer.buffer_info()[1], buffer.buffer_info()[0])
    result = fcntl.ioctl(sockfd.fileno(), SIOCGIFCONF, ifconf)

    # loop over interface names
    iflist = []
    size, ptr = struct.unpack("iP", result)
    for idx in range(0, size, 32):
        ifconf = buffer.tostring()[idx:idx+32]
        name, dummy = struct.unpack("16s16s", ifconf)
        name, dummy = name.split('\0', 1)
        iflist.append(name)

    return iflist


def getBroadcast(ifname):
    """ Get the broadcast addr for an interface """
    result = _call(ifname, SIOCGIFBRDADDR)
    return socket.inet_ntoa(result[20:24])


def getBroadcastList():
    brlist = ['<broadcast>']
    for ifname in getInterfaceList():
        if ifname != 'lo':
            brlist.append(getBroadcast(ifname))
    return brlist


def wake_on_lan(macaddress):
    """ Switches on remote computers using WOL. """

    # Check macaddress format and try to compensate.
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')
 
    print "Sending magic packet to", macaddress
    # Pad the synchronization stream.
    data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
    send_data = '' 

    # Split up the hex values and pack.
    for i in range(0, len(data), 2):
        send_data = ''.join([send_data,
                             struct.pack('B', int(data[i: i + 2], 16))])

    # Broadcast it to the LAN.
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for br in getBroadcastList():
        sockfd.sendto(send_data, (br, 9))

if __name__ == '__main__':
    for mac in sys.argv[1:]:
        wake_on_lan(mac)
