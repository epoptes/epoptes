# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Variables and functions to keep track of known clients and GUIs.
"""
import sys
from epoptes.core import logger

# stdout in epoptesd/bashplex/guiplex is handled by twisted and goes to syslog.
# stderr isn't, so tell Logger to use stdout.
LOG = logger.Logger(__file__, sys.stdout)

known_clients = {}
timed_out_clients = {}  # To distinguish reconnections from new connections
known_guis = []


def client_connected(handle, client):
    """Called from bashplex.py->connectionMade."""
    known_clients[handle] = client
    # Notify all known GUIs that an epoptes-client was connected
    for gui in known_guis:
        gui.client_connected(handle)


def client_disconnected(handle):
    """Called from bashplex.py->connectionLost."""
    if handle not in known_clients:
        LOG.e("Disconnect from unknown client: %s" % handle)
        return
    del known_clients[handle]
    # Notify all known GUIs that an epoptes-client was disconnected
    for gui in known_guis:
        gui.client_disconnected(handle)


def client_timed_out(handle):
    """Called from bashplex.py->ping_timed_out."""
    timed_out_clients[handle] = known_clients[handle]
    client_disconnected(handle)


def client_reconnected(handle):
    """Called from bashplex.py->ping_response."""
    client_connected(handle, timed_out_clients[handle])
    del timed_out_clients[handle]
