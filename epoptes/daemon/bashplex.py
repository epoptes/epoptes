# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Protocol for epoptesd.py <=> epoptes-client communication.
"""
from io import BytesIO
import os
import sys
import uuid

from twisted.internet import defer, protocol, reactor

from epoptes.core import logger
from epoptes.daemon import exchange


# stdout in epoptesd/bashplex/guiplex is handled by twisted and goes to syslog.
# stderr isn't, so tell Logger to use stdout.
LOG = logger.Logger(__file__, sys.stdout)


class DelimitedBashReceiver(protocol.Protocol):
    """Send bash commands followed by "\necho <delimiter>".
    Buffer responses until the given delimiter is found.
    """
    def __init__(self):
        self.buffer = BytesIO()
        self.current_delimiters = []  # A list of (delimiter, Deferred) tuples
        self.handle = None
        self.ping_timeout = None
        self.ping_timer = None
        self.timed_out = False

    def command(self, cmd, delimiter=None):
        """Send a command and return its associated Deferred.
        We don't do any state-checking here.
        If another command is in progress, it'll probably be okay,
        but if serialization is required, it should be done elsewhere.
        """
        if delimiter is None:
            # Template into which per-command delimiters are inserted.
            # Should include trailing newline.
            delimiter = bytes("__delimiter__{}__\n".format(uuid.uuid4()),
                              'utf-8')
        dfr = defer.Deferred()
        self.current_delimiters.append((delimiter, dfr))
        delimited_command = bytes(cmd, "utf-8") + b"\necho " + delimiter
        LOG.d("Sending:", delimited_command)
        self.transport.write(delimited_command)

        return dfr

    def check_for_further_responses(self):
        """See if there are more responses in the buffer.
        The theory here is that if we got one already, we have less than one
        packet of data left in the buffer, so reading it all isn't a big deal.
        """
        self.buffer.seek(0)
        rest = self.buffer.read()
        while self.current_delimiters:
            (delimiter, dfr) = self.current_delimiters[0]
            try:
                response, rest = rest.split(delimiter)
            except ValueError:
                break
            self.current_delimiters.pop(0)
            dfr.callback(response)
        new_buffer = BytesIO()
        new_buffer.write(rest)
        self.buffer = new_buffer

    def ping(self):
        """Periodically ping the clients."""
        self.command('ping').addCallback(self.ping_response)
        self.ping_timeout = reactor.callLater(
            self.factory.ping_timeout, self.ping_timed_out)

    def ping_response(self, _):
        """Receive the responses from the client pings."""
        # Responses that arrive after a client has timed out mean a "reconnect"
        if self.timed_out:
            LOG.w("Reconnected:", self.handle)
            exchange.client_reconnected(self.handle)
            self.timed_out = False
        else:
            self.ping_timeout.cancel()
        self.ping_timer = reactor.callLater(
            self.factory.ping_interval, self.ping)

    def ping_timed_out(self):
        """A response was not received for a ping within ping_timeout secs."""
        LOG.w("Ping timeout:", self.handle)
        self.timed_out = True
        exchange.client_timed_out(self.handle)

    def connectionMade(self):
        """Override BaseProtocol.connectionMade."""
        def forward_connection(_result):
            """Callback for startup_commands."""
            exchange.client_connected(self.handle, self)
            self.ping_timer = reactor.callLater(
                self.factory.ping_interval, self.ping)

        def kill_connection(error):
            """Errback for startup_commands."""
            LOG.e("Error: Could not send the startup functions to the client:",
                  error)
            self._loseConnection()

        peer = self.transport.getPeer()
        self.handle = "{}:{}".format(peer.host, peer.port)
        LOG.w("Connected:", self.handle)
        dfr = self.command(self.factory.startup_commands)
        dfr.addCallback(forward_connection)
        dfr.addErrback(kill_connection)

    def connectionLost(self, reason=protocol.connectionDone):
        """Override Protocol.connectionLost."""
        LOG.w("Connection lost:", self.handle)
        try:
            self.ping_timeout.cancel()
        except Exception:
            pass
        try:
            self.ping_timer.cancel()
        except Exception:
            pass
        if self.handle in exchange.known_clients:
            exchange.client_disconnected(self.handle)

    def dataReceived(self, data):
        """Override Protocol.dataReceived."""
        self.buffer.seek(0, os.SEEK_END)
        self.buffer.write(data)
        if not self.current_delimiters:
            return
        (delimiter, dfr) = self.current_delimiters[0]
        LOG.d("Searching for delimiter:", delimiter)
        # Optimize for big buffers by not searching the whole thing every time
        search_length = len(data) + len(delimiter)
        self.buffer.seek(-search_length, os.SEEK_END)
        search_str = self.buffer.read()
        search_pos = search_str.find(delimiter)
        if search_pos != -1:
            LOG.d("Found delimiter:", delimiter)
            # Two steps here is correct! If the delimiter was received in the
            # first packet, then the search_length is greater than the buffer
            # length, and doing this seek in one step gives the wrong answer.
            self.buffer.seek(-search_length, os.SEEK_END)
            self.buffer.seek(search_pos, os.SEEK_CUR)
            pos = self.buffer.tell()
            self.buffer.seek(0)
            response = self.buffer.read(pos)
            # Throw away the delimiter
            self.buffer.read(len(delimiter))
            new_buffer = BytesIO()
            new_buffer.write(self.buffer.read())
            self.buffer = new_buffer
            self.current_delimiters.pop(0)
            dfr.callback(response)
            self.check_for_further_responses()


class DelimitedBashReceiverFactory(protocol.ServerFactory):
    """Configuration variables for DelimitedBashReceiver."""
    protocol = DelimitedBashReceiver
    ping_interval = 10
    ping_timeout = 10
    startup_commands = ''
