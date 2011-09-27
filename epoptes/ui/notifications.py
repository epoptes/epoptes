#-*- coding: utf-8 -*-
import pynotify
import os

append = False

if not pynotify.init("epoptes-notifications"):
        sys.exit(1)

if 'x-canonical-append' in pynotify.get_server_caps():
    append = True

def notify(title, body, icon):
    n = pynotify.Notification(title, body, icon)
    n.set_hint_string("x-canonical-append", "");
    n.show()

def loggedinNotify(user, host):
    notify(_("Connected users:"), _("%(user)s on %(host)s") %{"user":user, "host":host},
                                "notification-message-im")
    
def loginNotify(user, host):
    notify(_("Connected:"), _("%(user)s on %(host)s") %{"user":user, "host":host}, 
                                "notification-message-im")

def logoutNotify(user, host):
    notify(_("Disconnected:"), _("%(user)s from %(host)s") %{"user":user, "host":host}, 
                                "notification-message-im")

def shutdownNotify(host):
    notify(_("Shut down:"), "%s" %(host), "notification-message-im")
