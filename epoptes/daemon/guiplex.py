#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# GUI plex.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
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

import os
import tempfile

from twisted.internet import protocol
from twisted.protocols import amp

import commands
import exchange

class GUI(amp.AMP):

    def connectionMade(self):
        amp.AMP.connectionMade(self)
        exchange.knownGUIs.append(self)


    def connectionLost(self, reason):
        amp.AMP.connectionLost(self, reason)
        exchange.knownGUIs.remove(self)


    def clientConnected(self, handle):
        self.callRemote(commands.ClientConnected, handle=handle)


    def clientDisconnected(self, handle):
        self.callRemote(commands.ClientDisconnected, handle=handle)


    @commands.EnumerateClients.responder
    def enumerateClients(self):
        return {'handles': sorted(exchange.knownClients.iterkeys())}


    @commands.ClientCommand.responder
    def clientCommand(self, handle, command):
        if handle not in exchange.knownClients:
            print " Unknown client %s, can't execute %s" %(handle,command)
            #raise ValueError("Unknown client")
            return {'filename': '', 'result': ''}

        d = exchange.knownClients[handle].command(command.encode("utf-8"))
        
        def sendResult(result):
            if len(result) > 65000:
                tf = tempfile.NamedTemporaryFile('wb', dir="/var/run/epoptes", delete=False)
                tf.write(result)
                os.fchmod(tf.file.fileno(), 0660)
                return {'filename': tf.name, 'result': ''}
            else:
                return {'result': result, 'filename': ''}

        d.addCallback(sendResult)
        return d


class GUIFactory(protocol.ServerFactory):
    protocol = GUI
