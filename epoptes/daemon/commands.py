#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# Commands.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
# 2018, Alkis Georgopoulos <alkisg@gmail.com>
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

from twisted.protocols import amp


class ClientConnected(amp.Command):
    arguments = [(b'handle', amp.Unicode())]
    response = []


class ClientDisconnected(amp.Command):
    arguments = [(b'handle', amp.Unicode())]
    response = []


class EnumerateClients(amp.Command):
    arguments = []
    response = [(b'handles', amp.ListOf(amp.Unicode()))]


class ClientCommand(amp.Command):
    arguments = [(b'handle', amp.Unicode()),
                 (b'command', amp.Unicode())]

    response = [(b'result', amp.String()),
                (b'filename', amp.Unicode())]
