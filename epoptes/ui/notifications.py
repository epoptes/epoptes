#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Notifications.
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
# MERCHANTABILITY or FINESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import pynotify
import os

if not pynotify.init("epoptes-notifications"):
    sys.exit(1)

append = 'x-canonical-append' in pynotify.get_server_caps()

def notify(title, body, icon):
    if not append:
        return False
    n = pynotify.Notification(title, body, icon)
    n.set_hint_string("x-canonical-append", "true")
    n.show()

def shutdownNotify(host):
    notify(_("Shut down:"), "%s" %(host), "notification-message-im")

def loginNotify(user, host):
    notify(_("Connected:"), _("%(user)s on %(host)s") %{"user":user, "host":host}, 
                                "notification-message-im")
def logoutNotify(user, host):
    notify(_("Disconnected:"), _("%(user)s from %(host)s") %{"user":user, "host":host}, 
                                "notification-message-im")

