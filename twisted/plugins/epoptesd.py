#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Communicate with epoptes-clients on SSL 789
and with GUIs on /run/epoptes/epoptes.socket.
Communcation flow:
  epoptesd.py imports bashplex.py <=SSL=> epoptes-client.
  epoptesd.py imports guiplex.py <=UNIX=> uiconnection imported by gui.py.
So, epoptesd, guiplex, bashplex and exchange run as root.
"""
import grp
import os

from OpenSSL import SSL
from zope.interface import implementer
from twisted.application import internet, service
from twisted.application.service import IServiceMaker
from twisted.internet import ssl
from twisted.python import usage
from twisted.plugin import IPlugin

from epoptes.common import config
from epoptes.daemon import bashplex, guiplex


class Options(usage.Options):
    """Define the epoptes service command line parameters."""
    optParameters = [
        ("client-port", "p", 789, "Client Port"),
        ('ping-interval', 'i', 10),
        ('ping-timeout', 't', 10)
    ]


class ServerContextFactory(ssl.ContextFactory):
    """Provide the SSL context."""
    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file("/etc/epoptes/server.crt")
        ctx.use_privatekey_file("/etc/epoptes/server.key")
        return ctx


def filter_bash(script):
    """Strip comments from client-functions, to save some bandwidth."""
    with open(script) as file:
        functions = file.readlines()
    result = ''
    for line in functions:
        if line.strip() != '' and line.strip()[0] == '#':
            continue
        result += line
    return result


@implementer(IServiceMaker, IPlugin)
class ServiceMaker(object):
    """Communicate with epoptes-clients on SSL 789
    and with GUIs on /run/epoptes/epoptes.socket.
    """
    tapname = "epoptes"
    description = "Epoptes Daemon"
    options = Options

    def makeService(self, options):
        """Override IServiceMaker.makeService."""
        factory = bashplex.DelimitedBashReceiverFactory()
        factory.ping_interval = int(options['ping-interval'])
        factory.ping_timeout = int(options['ping-timeout'])
        factory.startup_commands = filter_bash(
            '/usr/share/epoptes/client-functions')

        if config.system['ENCRYPTION']:
            client_service = internet.SSLServer(
                int(config.system['PORT']), factory, ServerContextFactory())
        else:
            client_service = internet.TCPServer(
                int(config.system['PORT']), factory)

        gid = grp.getgrnam(config.system['SOCKET_GROUP'])[2]

        if not os.path.isdir(config.system['DIR']):
            # TODO: for some reason this does 0750 instead
            os.makedirs(config.system['DIR'], 0o2770)
        os.chmod(config.system['DIR'], 0o2770)
        os.chown(config.system['DIR'], -1, gid)

        gui_service = internet.UNIXServer(
            "%s/epoptes.socket" % config.system['DIR'],
            guiplex.GUIFactory())

        top_service = service.MultiService()
        top_service.addService(client_service)
        top_service.addService(gui_service)

        return top_service


serviceMaker = ServiceMaker()
