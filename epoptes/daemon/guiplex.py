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
            raise ValueError("Unknown client")

        d = exchange.knownClients[handle].command(command.encode("utf-8"))

        def sendResult(result):
            if len(result) > 65000:
                tf = tempfile.NamedTemporaryFile('wb', dir="/tmp/epoptes", delete=False)
                tf.write(result)
                return {'filename': tf.name, 'result': ''}
            else:
                return {'result': result, 'filename': ''}

        d.addCallback(sendResult)
        return d


class GUIFactory(protocol.ServerFactory):
    protocol = GUI
