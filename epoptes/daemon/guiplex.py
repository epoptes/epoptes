# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Protocol for epoptesd.py <=> uiconnection.py communication.
"""
import os
import sys
import tempfile

from twisted.internet import protocol
from twisted.protocols import amp

from epoptes.core import logger
from epoptes.daemon import commands, exchange

# stdout in epoptesd/bashplex/guiplex is handled by twisted and goes to syslog.
# stderr isn't, so tell Logger to use stdout.
LOG = logger.Logger(__file__, sys.stdout)


class GUI(amp.AMP):
    """Protocol for epoptesd.py <=> uiconnection.py communication."""

    def connectionMade(self):
        """Override BaseProtocol.connectionMade."""
        super().connectionMade()
        exchange.known_guis.append(self)

    def connectionLost(self, reason):
        """Override AMP.connectionLost."""
        super().connectionLost(reason)
        exchange.known_guis.remove(self)

    def client_connected(self, handle):
        """Remotely call uiconnection.py->Daemon.client_connected."""
        self.callRemote(commands.ClientConnected, handle=handle)

    def client_disconnected(self, handle):
        """Remotely call uiconnection.py->Daemon.client_connected."""
        self.callRemote(commands.ClientDisconnected, handle=handle)

    @commands.EnumerateClients.responder
    def enumerate_clients(self):
        """Remotely called from uiconnection.py->Daemon.enumerate_clients."""
        return {'handles': sorted(exchange.known_clients.keys())}

    @commands.ClientCommand.responder
    def client_command(self, handle, command):
        """Remotely called from uiconnection.py->Daemon.command."""
        if handle not in exchange.known_clients:
            LOG.e("Unknown client %s, can't execute %s" % (handle, command))
            # raise ValueError("Unknown client")
            return {'filename': '', 'result': b''}

        dfr = exchange.known_clients[handle].command(command)

        def send_result(result):
            """Callback for bashplex.py->DelimitedBashReceiver.command."""
            if len(result) < 65000:
                return {'filename': '', 'result': result}
            tmpf = tempfile.NamedTemporaryFile('wb', dir="/run/epoptes",
                                               delete=False)
            tmpf.write(result)
            os.fchmod(tmpf.file.fileno(), 0o660)
            return {'filename': tmpf.name, 'result': b''}

        dfr.addCallback(send_result)
        return dfr


class GUIFactory(protocol.ServerFactory):
    """The factory for the GUI protocol."""
    protocol = GUI
