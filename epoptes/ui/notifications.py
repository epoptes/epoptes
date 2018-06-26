# This file is part of Epoptes, http://epoptes.org
# Copyright 2015-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Notifications.
Keep at most 10 lines of headings and messages.
A new bubble is created after 10 secs of inactivity.
That means that the oldest event may show for up to 9*10 seconds or so.

Example bubble layout:
[icon] Epoptes
*Connected:*
  user1 on host1
  user2 on host2
*Disconnected:*
  user3 from host3
*Shut down:*
  host4
*Connected:*
  user5 on host5

Notes for current server implementations (get_server_info, get_server_caps):
* bionic-ubuntu: no multiple bubbles,
    shows up to only 6 lines when hovered, merges '\n' otherwise,
    keeps history in the clock (one entry for all updates)
  (True, ret_name='gnome-shell', ret_vendor='GNOME',
    ret_version='3.28.1', ret_spec_version='1.2')
  ['actions', 'body', 'body-markup', 'icon-static', 'persistence', 'sound']
* bionic-mate: supports multiple bubbles
  (True, ret_name='Notification Daemon', ret_vendor='MATE',
    ret_version='1.20.0', ret_spec_version='1.1')
  ['actions', 'action-icons', 'body', 'body-hyperlinks', 'body-markup',
    'icon-static', 'sound']
* bionic-kubuntu: shows scrollbar after 10 messages,
    keeps history in the notification area (one entry per update!)
  (True, ret_name='Plasma', ret_vendor='KDE',
    ret_version='2.0', ret_spec_version='1.1')
  ['actions', 'body', 'body-hyperlinks', 'body-markup', 'icon-static']
* bionic-lubuntu (xfce4-notifyd): same as bionic-xubuntu
* bionic-xubuntu (xfce4-notifyd): closes on click (no [x] button)
  (True, ret_name='Xfce Notify Daemon', ret_vendor='Xfce',
    ret_version='0.4.2', ret_spec_version='1.2')
  ['actions', 'body', 'body-hyperlinks', 'body-markup', 'icon-static',
    'x-canonical-private-icon-only']
* stretch-gnome: same as bionic-ubuntu
* stretch-gnome (with notification-daemon -r): no multiple bubbles
  (True, ret_name='Notification Daemon', ret_vendor='GNOME',
    ret_version='3.20.0', ret_spec_version='1.2')
  ['actions', 'action-icons', 'body', 'body-hyperlinks', 'body-markup',
    'icon-static', 'persistence', 'sound']
* sylvia-cinnamon:
  (True, ret_name='cinnamon', ret_vendor='GNOME',
    ret_version='3.6.7', ret_spec_version='1.2')
  ['actions', 'action-icons', 'body', 'body-markup', 'icon-static',
    'persistence']
* xenial-ubuntu:
  (True, ret_name='notify-osd', ret_vendor='Canonical Ltd',
    ret_version='1.0', ret_spec_version='1.1')
  ['body', 'body-markup', 'icon-static', 'image/svg+xml',
    'x-canonical-private-synchronous', 'x-canonical-append',
    'x-canonical-private-icon-only', 'x-canonical-truncation',
    'private-synrchronous', 'append', 'private-icon-only', 'truncation']
"""
import time

from epoptes.common import gettext as _
from gi.repository import Notify


class NotifyQueue:
    """A special queue that keeps at most 10 lines of headings and messages."""
    initialized = None

    def __init__(self, summary, icon):
        """Initialize Notify and local variables."""
        if not NotifyQueue.initialized:
            NotifyQueue.initialized = True
            if not Notify.init("Epoptes"):
                raise ImportError(_('Could not initialize notifications!'))
        self.summary = summary
        self.icon = icon
        self.items = []
        # The heading of the last item enqueued
        self.last_heading = ''
        self.last_time = time.time()
        self.notification = None

    def enqueue(self, heading, msg):
        """Add a new message to the queue, and show it."""
        # Create a new bubble if 10 secs have passed from the last notification
        now = time.time()
        if now - self.last_time > 10:
            self.__init__(self.summary, self.icon)
        self.last_time = now
        if heading != self.last_heading:
            self.last_heading = heading
            self.items.append("<b>{}</b>".format(heading))
        self.items.append("  {}".format(msg))
        # One enqueue may insert both heading and msg, needing 2 dequeues
        while len(self.items) > 10:
            self.dequeue()
        self.show()

    def dequeue(self):
        """Delete the first message after the first heading.
        If the section is now empty, delete the first heading as well."""
        del self.items[1]
        if (not self.items) \
                or (len(self.items) > 1 and self.items[1].startswith('<b>')):
            del self.items[0]

    def to_string(self):
        """Return a string of all queued messages."""
        return '\n'.join(self.items)

    @staticmethod
    def new_notification(summary, body, icon):
        """Create a new notification object. Called by show()."""
        result = Notify.Notification.new(summary, body, icon)
        result.set_urgency(Notify.Urgency.LOW)
        result.set_hint_string('desktop-entry', 'epoptes')
        # This tells GNOME not to log the notification
        result.set_hint_string('transient', 'true')
        return result

    def show(self):
        """Create, update, or re-create the notification, and show it."""
        if self.notification is None:
            self.notification = self.new_notification(
                self.summary, self.to_string(), self.icon)
        elif not self.notification.update(
                self.summary, self.to_string(), self.icon):
            self.notification = self.new_notification(
                self.summary, self.to_string(), self.icon)
        self.notification.show()


def main():
    """Run a notifications test from the command line.
    If epoptes isn't installed, `import epoptes.common` needs to be removed."""
    print("get_server_info =", Notify.get_server_info())
    print("get_server_caps =", Notify.get_server_caps())
    events = [
        ("Connected:", "user1 on host1"),
        ("Connected:", "user2 on host2"),
        ("Disconnected:", "user3 from host3"),
        ("Shut down:", "host4"),
        ("Connected:", "user5 on host5"),
        ("Connected:", "user6 on host6"),
        ("Shut down:", "host7"),
        ("Shut down:", "host8"),
        ("Connected:", "user9 on host9"),
        ("Connected:", "user10 on host10")
    ]
    i = 0
    notq = NotifyQueue('Epoptes', 'dialog-information')
    while i < len(events):
        notq.enqueue(events[i][0], events[i][1])
        time.sleep(1)
        i += 1
        if i == 5:
            # Wait for the bubble to autoclose, then a new one should show up
            time.sleep(10)


if __name__ == '__main__':
    main()
