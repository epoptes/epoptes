import os
from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service

from epoptes.daemon import bashplex, guiplex
#import ConfigParser
#conf = ConfigParser.ConfigParser()
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
        
        #conf.read("/etc/default/epoptes")
        #if conf.has_option("Daemon", "owner_group"):
        #    import grp
        #    gid = grp.getgrnam(conf.get("Daemon", "owner_group"))[2]
        #else:
        #    gid = -1
        gid = grp.getgrnam(config.system['SOCKET_GROUP'])[2]
        
        #if conf.has_option("Daemon", "path"):
        #    dir = conf.get("Daemon", "path")
        #else:
        #    dir = "/tmp/epoptes"

        dir = "/tmp/epoptes"
        if not os.path.isdir(dir):
            #TODO: for some reason this does 0750 instead
            os.makedirs(dir, 02770)
        os.chmod(dir, 02770)
        os.chown(dir, -1, gid)

        guiService = internet.UNIXServer(
            "%s/epoptes.socket" % dir,
            guiplex.GUIFactory())

        topService = service.MultiService()
        topService.addService(clientService)
        topService.addService(guiService)

        return topService


serviceMaker = ServiceMaker()
