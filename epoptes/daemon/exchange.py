#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# Global registry type stuff.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
# 2018, Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

"""
Global registry type stuff
"""

knownClients = {}
timedOutClients = {}
knownGUIs = []


def clientConnected(handle, client):
    # print("Client connected: %s" % handle.encode("utf-8"))
    knownClients[handle] = client
    for gui in knownGUIs:
        gui.clientConnected(handle)


def clientDisconnected(handle):
    if handle not in knownClients:
        print("Disconnect from unknown client: %s" % handle.encode("utf-8"))
        return

    # print("Client disconnected: %s" % handle.encode("utf-8"))
    del knownClients[handle]
    for gui in knownGUIs:
        gui.clientDisconnected(handle)


def clientTimedOut(handle):
    timedOutClients[handle] = knownClients[handle]
    clientDisconnected(handle)


def clientReconnected(handle):
    clientConnected(handle, timedOutClients[handle])
    del timedOutClients[handle]
