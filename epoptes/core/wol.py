#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Power on remote computers using Wake On LAN.
"""
import socket
import sys

import netifaces


def get_broadcast_list():
    """Return all broadcast addresses.
    E.g. WOL messages need to be sent from all NICs.
    """
    brlist = ['<broadcast>']
    ifaces = [iface for iface in netifaces.interfaces() if iface != 'lo']
    for ifname in ifaces:
        # An interface can have more than one address, even within the
        # same family (AF_INET), or none, so check this case too.
        addresses = netifaces.ifaddresses(ifname)
        if netifaces.AF_INET not in addresses:
            continue
        for addr in addresses[netifaces.AF_INET]:
            if 'broadcast' in addr:
                brlist.append(addr['broadcast'])
    return brlist


def wake_on_lan(macaddress):
    """Power on remote computers using Wake On LAN."""
    # Handle MACs with or without separators.
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')

    print("Sending magic packet to", macaddress)
    packet = bytes.fromhex(''.join(['FFFFFFFFFFFF', macaddress * 20]))

    # Broadcast it to the LAN.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for brd in get_broadcast_list():
        sock.sendto(packet, (brd, 9))


def main():
    """Run the module from the command line."""
    for mac in sys.argv[1:]:
        wake_on_lan(mac)


if __name__ == '__main__':
    main()
