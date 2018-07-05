# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Commands used for guiplex.py <=> uiconnection.py AMP-based communication.
"""
from twisted.protocols import amp


class ClientConnected(amp.Command):
    """Command for guiplex.py->GUI.client_connected
     to remotely call uiconnection.py->Daemon.client_connected.
     """
    arguments = [(b'handle', amp.Unicode())]
    response = []


class ClientDisconnected(amp.Command):
    """Command for guiplex.py->GUI.client_disconnected
     to remotely call uiconnection.py->Daemon.client_disconnected.
     """
    arguments = [(b'handle', amp.Unicode())]
    response = []


class EnumerateClients(amp.Command):
    """Command for uiconnection.py->Daemon.enumerate_clients
     to remotely call guiplex.py->GUI.enumerate_clients.
     """
    arguments = []
    response = [(b'handles', amp.ListOf(amp.Unicode()))]


class ClientCommand(amp.Command):
    """Command for uiconnection.py->Daemon.command
     to remotely call guiplex.py->GUI.command.
     """
    arguments = [(b'handle', amp.Unicode()),
                 (b'command', amp.Unicode())]
    response = [(b'result', amp.String()),
                (b'filename', amp.Unicode())]
