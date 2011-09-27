#-*- coding: utf-8 -*-
import os

from twisted.internet import protocol
from twisted.protocols import amp

import commands

class Daemon(amp.AMP):

    def __init__(self, client):
        self.client = client


    def connectionMade(self):
        amp.AMP.connectionMade(self)
        self.client.connected(self)
        
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

