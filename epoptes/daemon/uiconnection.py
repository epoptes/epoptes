# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GUI-side part of the gui.py <=UNIX=> guiplex.py protocol.
"""
import os

from twisted.protocols import amp

from epoptes.daemon import commands


class Daemon(amp.AMP):
    """GUI-side part of the gui.py <=UNIX=> guiplex.py protocol."""
    def __init__(self, client):
        super().__init__()
        self.client = client

    def connectionMade(self):
        """Override BaseProtocol.connectionMade."""
        super().connectionMade()
        # We've connected the GUI to the Daemon.
        # Call gui.py->EpoptesGui.connected to store a reference to daemon.
        self.client.connected(self)

    def connectionLost(self, reason):
        """Override AMP.connectionLost."""
        super().connectionLost(reason)
        self.client.disconnected(self)

    @commands.ClientConnected.responder
    def client_connected(self, handle):
        """Remotely called from guiplex.py->GUI.client_connected."""
        # Call gui.py->EpoptesGui.amp_client_connected.
        self.client.amp_client_connected(handle)
        return {}

    @commands.ClientDisconnected.responder
    def client_disconnected(self, handle):
        """Remotely called from guiplex.py->GUI.client_disconnected."""
        # Call gui.py->EpoptesGui.amp_client_disconnected.
        self.client.amp_client_disconnected(handle)
        return {}

    def enumerate_clients(self):
        """Remotely call guiplex.py->GUI.enumerate_clients."""
        dfr = self.callRemote(commands.EnumerateClients)
        dfr.addCallback(lambda r: r['handles'])
        return dfr

    def command(self, handle, command):
        """Remotely call guiplex.py->GUI.command."""
        dfr = self.callRemote(commands.ClientCommand,
                              handle=handle,
                              command=command)

        def got_result(response):
            """Callback for guiplex.py->GUI.command."""
            filename = response['filename']
            if filename:
                result = open(filename, 'rb').read()
                os.unlink(filename)
                return result
            return response['result']

        dfr.addCallback(got_result)
        return dfr
