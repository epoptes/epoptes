import os
from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service

from epoptes.daemon import bashplex, guiplex
from epoptes.common import config
import grp


class Options(usage.Options):
    optParameters = [
        ("clientport", "p", 569, "Client Port"),
        ('pingInterval', 'i', 10),
        ('pingTimeout', 't', 10),
      ]


class ServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "epoptes"
    description = "Epoptes Daemon"
    options = Options

    def makeService(self, options):
        
        factory = bashplex.DelimitedBashReceiverFactory()
        factory.pingInterval=int(options['pingInterval'])
        factory.pingTimeout=int(options['pingTimeout'])

        clientService = internet.TCPServer(int(config.system['PORT']), factory)
        
        gid = grp.getgrnam(config.system['SOCKET_GROUP'])[2]
        
        if not os.path.isdir(config.system['DIR']):
            #TODO: for some reason this does 0750 instead
            os.makedirs(config.system['DIR'], 02770)
        os.chmod(config.system['DIR'], 02770)
        os.chown(config.system['DIR'], -1, gid)

        guiService = internet.UNIXServer(
            "%s/epoptes.socket" % config.system['DIR'],
            guiplex.GUIFactory())

        topService = service.MultiService()
        topService.addService(clientService)
        topService.addService(guiService)

        return topService


serviceMaker = ServiceMaker()
