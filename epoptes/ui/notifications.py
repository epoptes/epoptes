#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Notifications.
#
# Copyright (C) 2015 Fotis Tsamis <ftsamis@gmail.com>
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


class NotificationCache(object):
    """A class to store notifications by 'summary' until they get closed/hidden.
    This helps to emulate the x-canonical-append capability on systems that
    do not provide it.
    """
    def __init__(self):
        self.notifications = {}

    def add_notification(self, n, title):
        # The title argument is important to handle unicode summaries correctly.
        # n.props.summary does not return unicode objects.
        self.notifications[title] = n
        n.connect("closed", self.remove_notification, title)

    def get_notification(self, title):
        if title in self.notifications:
            return self.notifications[title]

    def remove_notification(self, n, title):
        # The title argument is important to handle unicode summaries correctly.
        del self.notifications[title]


def notify(title, body, icon):
    n = pynotify.Notification(title, body, icon)
    n.set_hint_string("x-canonical-append", "true")
    n.show()


def cached_notify(title, body, icon):
    """A function to replace pynotify.notify if the 'x-canonical-append'
    capability is not provided.
    """
    n = cache.get_notification(title)
    if n:
        n.close()
        n.update(title, n.props.body+'\n'+body, icon)
    else:
        n = pynotify.Notification(title, body, icon)
        cache.add_notification(n, title)
    n.show()


append = 'x-canonical-append' in pynotify.get_server_caps()
if not append:
    cache = NotificationCache()
    notify = cached_notify

def shutdownNotify(host):
    notify(_("Shut down:"), "%s" %(host), os.path.abspath("images/shutdown.svg"))

def loginNotify(user, host):
    notify(_("Connected:"), _("%(user)s on %(host)s") %{"user":user, "host":host},
                                os.path.abspath("images/login.svg"))
def logoutNotify(user, host):
    notify(_("Disconnected:"), _("%(user)s from %(host)s") %{"user":user, "host":host},
                                os.path.abspath("images/logout.svg"))

