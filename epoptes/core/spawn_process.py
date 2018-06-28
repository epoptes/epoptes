#!/usr/bin/env python3
# This file is part of Epoptes, http://epoptes.org
# Copyright 2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Spawn a process asynchronously and get its output in a callback.
https://twistedmatrix.com/documents/current/core/howto/process.html
The spawned process may be terminated:
 * By itself with exit code = 0 (success)
 * By itself with exit code != 0 (failure)
 * By SpawnProcess when lines_max is reached (success)
 * By SpawnProcess when timeout is reached (failure)
 * By the caller (e.g. a cancel button) using SpawnProcess.stop() (failure)
It's possible that some useful stdout exists even on failure.
"""
from twisted.internet import protocol, reactor

from epoptes.core import logger


LOG = logger.Logger(__file__)


class SpawnProcess(protocol.ProcessProtocol):
    """Spawn a process asynchronously and get its output in a callback."""
    def __init__(self, on_exit):
        self.dc_stop = None  # IDelayedCall, to cancel the stop callback
        self.dc_timeout = None  # IDelayedCall, to cancel the timeout callback
        self.err_data = b''
        self.lines_count = 0
        self.lines_max = 0
        self.on_exit = on_exit
        self.out_data = b''
        self.reason = ''
        self.state = 'idle'  # or: running, stopping1, stopping2, stopping3

    def __del__(self):
        """Kill child processes even on abrupt exits."""
        LOG.d("__del__:")
        if self.state == "running":
            self.stop('destructor')

    def spawn(self, cmdline, timeout=0, lines_max=0):
        """Spawn the process and run on_exit on exit, timeout, or lines_max."""
        LOG.d("spawn: {}, timeout: {}, lines_max: {}".format(
            cmdline, timeout, lines_max))
        assert self.state == "idle"
        # Reinitialize vars without duplicating a lot of code
        self.__init__(self.on_exit)
        self.lines_max = lines_max
        if timeout:
            self.dc_timeout = reactor.callLater(timeout, self.stop, "timeout")
        else:
            self.dc_timeout = None
        # Meh unknown ref, https://youtrack.jetbrains.net/issue/PY-1490
        reactor.spawnProcess(self, cmdline[0], cmdline)

    def stop(self, reason=""):
        """Send TERM, TERM, KILL, with 0.5 sec delays."""
        LOG.d("stop('{}')".format(reason))
        assert self.state != "idle"
        assert self.transport
        # Once stopping started, only accept calls from stop itself,
        # and not for example lines_max calls.
        if self.state.startswith("stopping") \
                and not reason.startswith("stopping"):
            return
        # Only keep the initial reason
        if not self.reason:
            self.reason = reason
        # Cancel the timeout callback
        if self.dc_timeout:
            if self.reason != "timeout":
                self.dc_timeout.cancel()
            self.dc_timeout = None
        if self.state == "running":
            self.state = "stopping1"
            self.transport.signalProcess('TERM')
        elif self.state == "stopping1":
            self.state = "stopping2"
            # iperf2 requests 2 TERM signals to abort waiting open connections
            # Additionally, help it by closing its stdio
            self.transport.loseConnection()
            self.transport.signalProcess('TERM')
        elif self.state == "stopping2":
            self.state = "stopping3"
            # Kill it, don't wait any longer
            self.transport.signalProcess('KILL')
        else:
            assert False, "Unable to kill child process!"
        self.dc_stop = reactor.callLater(0.5, self.stop, self.state)

    def connectionMade(self):
        """Override BaseProtocol.connectionMade."""
        LOG.d("connectionMade: pid =", self.transport.pid)
        self.state = 'running'

    def errReceived(self, data):
        """Override ProcessProtocol.errReceived."""
        LOG.d("errReceived:", data)
        self.err_data += data

    def outReceived(self, data):
        """Override ProcessProtocol.outReceived."""
        old_lines_count = self.lines_count
        self.lines_count += data.count(b'\n')
        LOG.d("outReceived, lines_count = %s:" % self.lines_count, data)
        self.out_data += data
        # If this is the first time lines_max is exceeded, call stop
        if self.lines_count >= self.lines_max > old_lines_count:
            self.stop("lines_max")

    def processExited(self, reason):
        """Override ProcessProtocol.processExited."""
        LOG.d("processExited:", reason.value.exitCode)
        self.state = "idle"
        # Cancel the timeout and stop callbacks
        if self.dc_timeout:
            self.dc_timeout.cancel()
            self.dc_timeout = None
        if self.dc_stop:
            self.dc_stop.cancel()
            self.dc_stop = None
        if not self.reason:
            self.reason = str(reason.value)
        reactor.callLater(0, self.call_on_exit)

    def call_on_exit(self):
        """Call on_exit after processing all twisted events.
        When e.g. the iperf port is already in use, processExited happens
        before errReceived gets "bind failed: Address already in use".
        Using callLater, on_exit is able to properly get and display stderr.
        """
        self.on_exit(self.out_data, self.err_data, self.reason)


def main():
    """Run a test from the command line."""

    def on_test_exit(out_data, err_data, reason):
        """Called by SpawnProcess when the test process exits."""
        LOG.d("  Callback out_data:", out_data)
        LOG.d("  Callback err_data:", err_data)
        LOG.d("  Callback reason:", reason)
        # Quit a bit later in order to test if events occur properly
        reactor.callLater(3, reactor.stop)

    script = """# Produce some output with delays
i=0
while [ $i -lt 5 ]; do
    echo "process stdout line #$i"
    echo "process stderr line #$i" >&2
    sleep 1
    i=$(($i+1))
done
"""
    tests = ['process-error']
    print("Running tests:", tests)
    if 'normal-termination' in tests:
        SpawnProcess(on_test_exit).spawn(['sh', '-c', script])
    if 'lines_max' in tests:
        SpawnProcess(on_test_exit).spawn(
            ['sh', '-c', 'trap "" TERM\n' + script], lines_max=3)
    if 'timeout' in tests:
        SpawnProcess(on_test_exit).spawn(['sh', '-c', script], timeout=3)
    if 'event-driven' in tests:  # e.g. a cancel button
        proc = SpawnProcess(on_test_exit)
        proc.spawn(['sh', '-c', script])
        reactor.callLater(3, proc.stop, 'cancelled')
    if 'process-error' in tests:
        SpawnProcess(on_test_exit).spawn(
            ['sh', '-c', 'echo Started && sleep 1 && invalid-command'])

    reactor.run()


if __name__ == '__main__':
    main()
