#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Epoptesd.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import os
from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service

from epoptes.daemon import bashplex, guiplex
from epoptes.common import config
import grp
from OpenSSL import SSL


class Options(usage.Options):
    optParameters = [
        ("clientport", "p", 789, "Client Port"),
        ('pingInterval', 'i', 10),
        ('pingTimeout', 't', 10),
      ]


class ServerContextFactory:
    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file("/etc/epoptes/server.crt")
        ctx.use_privatekey_file("/etc/epoptes/server.key")
        return ctx


class ServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "epoptes"
    description = "Epoptes Daemon"
    options = Options

    def makeService(self, options):
        
        factory = bashplex.DelimitedBashReceiverFactory()
        factory.pingInterval=int(options['pingInterval'])
        factory.pingTimeout=int(options['pingTimeout'])
        factory.startupCommands = self.filterBash('/usr/share/epoptes/client-functions')

        if config.system['ENCRYPTION']:
            clientService = internet.SSLServer(int(config.system['PORT']),
                factory, ServerContextFactory())
        else:
            clientService = internet.TCPServer(int(config.system['PORT']),
                factory)

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
    
    def filterBash(self, script):
        f = open(script)
        functions = f.readlines()
        f.close()
        
        result = ''
        
        for line in functions:
            if line.strip() != '' and line.strip()[0] == '#':
                continue
            result += line
        return result

serviceMaker = ServiceMaker()
