#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# UI connection.
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

import os

from twisted.internet import protocol
from twisted.protocols import amp

from . import commands


class Daemon(amp.AMP):

    def __init__(self, client):
        self.client = client

    def connectionMade(self):
        amp.AMP.connectionMade(self)
        self.client.connected(self)

    def connectionLost(self, reason):
        amp.AMP.connectionLost(self, reason)
        self.client.disconnected(self)

    @commands.ClientConnected.responder
    def clientConnected(self, handle):
        self.client.amp_clientConnected(handle)
        return {}

    @commands.ClientDisconnected.responder
    def clientDisconnected(self, handle):
        self.client.amp_clientDisconnected(handle)
        return {}

    def enumerateClients(self):
        d = self.callRemote(commands.EnumerateClients)
        d.addCallback(lambda r: r['handles'])
        return d

    def command(self, handle, command):
        d = self.callRemote(commands.ClientCommand,
                            handle=handle,
                            command=command)

        def gotResult(response):
            filename = response['filename']
            if filename:
                result = open(filename, 'rb').read()
                os.unlink(filename)
                return result
            else:
                return response['result']

        d.addCallback(gotResult)
        return d
