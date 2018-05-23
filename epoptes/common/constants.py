#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# Common constants.
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

# Warn users to update their chroots if they have a lower epoptes-client version 
# than this
COMPATIBILITY_VERSION = (0, 5)

# ['ltsp123', '00-1b-24-89-65-d6', '127.0.0.1:46827', '10.160.31.126:44920', 
#  'thin', 'user3', <gtk.gdk.Pixbuf>, '10.160.31.123', 'user (ltsp123)']
C_LABEL = 0
C_PIXBUF = 1
C_INSTANCE = 2
C_SESSION_HANDLE = 3
# [label, <gtk.gdk.Pixbuf>, <Client instance>, username]
G_LABEL = 0
G_INSTANCE = 1

# Execution Modes are used in execOnClients
EM_SESSION_ONLY = 0
EM_SYSTEM_ONLY = 1
EM_EXIT_IF_SENT = 2
EM_SESSION = [EM_SESSION_ONLY]
EM_SESSION_AND_SYSTEM = [EM_SESSION_ONLY, EM_SYSTEM_ONLY]
EM_SESSION_OR_SYSTEM = [EM_SESSION_ONLY, EM_EXIT_IF_SENT, EM_SYSTEM_ONLY]
EM_SYSTEM_OR_SESSION = [EM_SYSTEM_ONLY, EM_EXIT_IF_SENT, EM_SESSION_ONLY]
EM_SYSTEM_AND_SESSION = [EM_SYSTEM_ONLY, EM_SESSION_ONLY]
EM_SYSTEM = [EM_SYSTEM_ONLY]
