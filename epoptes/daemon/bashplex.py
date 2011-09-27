import os
import uuid

from twisted.internet import reactor, protocol, defer

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import exchange


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
        self.buffer = StringIO()
        self.pingTimer = None
        self.pingTimeout = None


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

        print "Sending:", delimitedCommand,
        self.transport.write(delimitedCommand)

        return d


    def connectionMade(self):
        peer = self.transport.getPeer()
        self.handle = u"%s:%s" % (peer.host, peer.port)
        exchange.clientConnected(self.handle, self)
        self.pingTimer = reactor.callLater(self.factory.pingInterval, self.ping)


    def connectionLost(self, reaspn):
        try: self.pingTimeout.cancel()
        except Exception: pass

        try: self.pingTimer.cancel()
        except Exception: pass

        exchange.clientDisconnected(self.handle)


    def dataReceived(self, data):
        self.buffer.seek(0, os.SEEK_END)
        self.buffer.write(data)

        if not self.currentDelimiters:
            return

        (delimiter, d) = self.currentDelimiters[0]

        # Optimize for large buffers by not searching the whole thing every time
        searchLength = len(data) + len(delimiter)

        self.buffer.seek(-searchLength, os.SEEK_END)

        searchStr = self.buffer.read()
        searchPos = searchStr.find(delimiter)
        if searchPos != -1:

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

            newBuffer = StringIO()
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
                
        newBuffer = StringIO()
        newBuffer.write(rest)
        self.buffer = newBuffer
    
                
    def ping(self):
        if self.pingTimeout is not None:
            return

        self.command("test -d /proc/$PPID || exit").addCallback(self.pingResponse)
        self.pingTimeout = reactor.callLater(self.factory.pingTimeout, 
                                             self.pingTimedOut)

    def pingResponse(self, _):
        self.pingTimeout.cancel()
        self.pingTimeout = None
        self.pingTimer = reactor.callLater(self.factory.pingInterval, self.ping)


    def pingTimedOut(self):
        print "Ping timeout!"
        self.transport.loseConnection()


class DelimitedBashReceiverFactory(protocol.ServerFactory):
    protocol = DelimitedBashReceiver
    
    pingInterval = 10
    pingTimeout = 10
