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

import sys
import socket
import struct
import netifaces

def getBroadcastList():
    brlist = ['<broadcast>']
    for ifname in netifaces.interfaces:
        if ifname != 'lo':
            for addr in netifaces.ifaddresses(ifname)[netifaces.AF_INET]:
                if 'broadcast' in addr:
                    brlist.append(addr['broadcast'])
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for br in getBroadcastList():
        sock.sendto(send_data, (br, 9))

if __name__ == '__main__':
    for mac in sys.argv[1:]:
        wake_on_lan(mac)
