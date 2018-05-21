#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# BASH plex.
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
import uuid
from twisted.internet import reactor, protocol, defer, error
from io import BytesIO

from . import exchange


class DelimitedBashReceiver(protocol.Protocol):
    """
    Send bash commands followed by "\necho <delimiter>",
    buffer responses until the given delimiter is found.
    """

    # Template into which per-command delimiters are
    # inserted. Should include trailing newline.
    delimiterTemplate = "__delimiter__%s__\n"

    def __init__(self):
        self.currentDelimiters = []
        self.buffer = BytesIO()
        self.pingTimer = None
        self.pingTimeout = None
        self.timedOut = False


    def getDelimiter(self):
        """
        Generate a per-command delimiter. We could
        use a sequence number here instead, but I'm
        not sure we could do any more useful error
        handling with it.
        """
        return str(uuid.uuid4())


    def command(self, cmd, delimiter=None):
        """
        Send a command. We don't do any state-checking
        here. If another command is in progress, it'll
        probably be okay, but if serialization is required,
        it should be done elsewhere.
        """

        if delimiter is None:
            delimiter = self.delimiterTemplate % self.getDelimiter()

        d = defer.Deferred()

        self.currentDelimiters.append((delimiter, d))

        delimitedCommand = "%s\necho %s" % (
            cmd, delimiter)

        # TODO: check the python's debug logging implementation
        # print("Sending:", str(delimitedCommand))
        self.transport.write(bytes(delimitedCommand, 'utf-8'))

        return d


    def connectionMade(self):
        peer = self.transport.getPeer()
        self.handle = "%s:%s" % (peer.host, peer.port)
        print("Connected:", self.handle)
        
        d = self.command(self.factory.startupCommands)
        
        def forwardConnection(result):
            exchange.clientConnected(self.handle, self)
            self.pingTimer = reactor.callLater(self.factory.pingInterval, self.ping)
        
        def killConnection(error):
            print("Error: Could not send the startup functions to the client:", error)
            self._loseConnection()
        
        d.addCallback(forwardConnection)
        d.addErrback(killConnection)


    def connectionLost(self, reason):
        print("Connection lost:", self.handle)
        
        try: self.pingTimeout.cancel()
        except Exception: pass

        try: self.pingTimer.cancel()
        except Exception: pass

        if self.handle in exchange.knownClients:
            exchange.clientDisconnected(self.handle)


    def dataReceived(self, data):
        self.buffer.seek(0, os.SEEK_END)
        self.buffer.write(data)

        if not self.currentDelimiters:
            return

        (delimiter, d) = self.currentDelimiters[0]
        #print "Searching for delimiter:", delimiter

        # Optimize for large buffers by not searching the whole thing every time
        searchLength = len(data) + len(delimiter)

        self.buffer.seek(-searchLength, os.SEEK_END)

        searchStr = self.buffer.read()
        searchPos = searchStr.find(bytes(delimiter, 'ascii'))
        if searchPos != -1:
            #print "Found delimiter:", delimiter

            # Two steps here is correct! If the delimiter was received in the
            # first packet, then the searchLength is greater than the buffer
            # length, and doing this seek in one step gives the wrong answer.
            self.buffer.seek(-searchLength, os.SEEK_END)
            self.buffer.seek(searchPos, os.SEEK_CUR)
            pos = self.buffer.tell()

            self.buffer.seek(0)
            response = self.buffer.read(pos)

            # Throw away the delimiter
            self.buffer.read(len(delimiter))

            newBuffer = BytesIO()
            newBuffer.write(self.buffer.read())
            self.buffer = newBuffer

            self.currentDelimiters.pop(0)
            d.callback(response)

            self.checkForFurtherResponses()


    def checkForFurtherResponses(self):
        # See if there are more responses in the buffer. 
        # The theory here is that if we got one already, we have less than one
        # packet of data left in the buffer, so reading it all isn't a big deal

        self.buffer.seek(0)
        rest = self.buffer.read()

        while self.currentDelimiters:
            (delimiter, d) = self.currentDelimiters[0]
            try:
                response, rest = rest.split(delimiter)
            except ValueError:
                break
                        
            self.currentDelimiters.pop(0)
            d.callback(response)
                
        newBuffer = BytesIO()
        newBuffer.write(rest)
        self.buffer = newBuffer


    def ping(self):
        self.command('ping').addCallback(self.pingResponse)
        self.pingTimeout = reactor.callLater(self.factory.pingTimeout, 
                                             self.pingTimedOut)

    def pingResponse(self, _):
        # Responses that arrive after a client has timed out, mean a "reconnect"
        if self.timedOut:
            print("Reconnected:", self.handle)
            exchange.clientReconnected(self.handle)
            self.timedOut = False
        else:
            self.pingTimeout.cancel()
        self.pingTimer = reactor.callLater(self.factory.pingInterval, self.ping)


    def pingTimedOut(self):
        print("Ping timeout:", self.handle)
        self.timedOut = True
        exchange.clientTimedOut(self.handle)


class DelimitedBashReceiverFactory(protocol.ServerFactory):
    protocol = DelimitedBashReceiver
    
    pingInterval = 10
    pingTimeout = 10
    
    startupCommands = ''
