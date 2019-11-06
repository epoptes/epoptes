#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Lock the screen.
"""
import sys

from _common import gettext as _
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


class LockScreen:
    """Lock the screen."""
    def __init__(self, from_main=False):
        self.backlock = None
        self.from_main = from_main
        self.frontview = None
        self.label = None

    def lock(self, msg, unlock_secs=None):
        """Lock the screen. Unlock after unlock_secs if it's not None."""
        screen = Gdk.Screen.get_default()
        swidth = screen.get_width()
        sheight = screen.get_height()
        smin = min(swidth, sheight)

        gtk_provider = Gtk.CssProvider()
        gtk_context = Gtk.StyleContext()
        gtk_context.add_provider_for_screen(
            screen, gtk_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        gtk_provider.load_from_data(bytes("""
* {{ transition-property: color;  transition-duration: 4s; }}
window, GtkWindow {{ background-color: black; }}
label, GtkLabel {{ font-size: {0:.0f}px; }}
label#black, GtkLabel#black {{ color: black; }}
label#white, GtkLabel#white {{ color: #e0e0e0; }}
""".format(swidth / 70).encode()))

        backlock = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.backlock = backlock
        backlock.resize(1, 1)
        frontview = Gtk.Window()
        self.frontview = frontview
        frontview.resize(swidth, sheight)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=smin/12,
            halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        image = Gtk.Image(pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_size(
            'lock.svg', smin/3, smin/3))
        box.pack_start(image, False, False, 0)
        self.label = Gtk.Label(label=msg, name="black")
        box.pack_start(self.label, False, False, 0)
        frontview.add(box)

        backlock.show_all()
        frontview.show_all()

        frontview.set_keep_above(True)
        frontview.fullscreen()
        Gdk.beep()
        Gdk.keyboard_grab(backlock.get_window(), False, 0)

        # Transitions need an event to start
        GLib.timeout_add(100, self.do_transition)

        # While developing, to only lock the screen for e.g. 5 seconds, run:
        # ./lock-screen "" 5
        if unlock_secs is not None:
            GLib.timeout_add(unlock_secs*1000, self.unlock)

    def do_transition(self):
        """Change the label id, so that the fade in effect is started."""
        self.label.set_name("white")

    def unlock(self):
        """Unlock the screen. Also exit Gtk if called from main."""
        Gdk.keyboard_ungrab(0)
        self.backlock.destroy()
        self.frontview.destroy()
        if self.from_main:
            Gtk.main_quit()


def main():
    """Run the module from the command line."""
    if len(sys.argv) > 1 and sys.argv[1]:
        msg = sys.argv[1]
    else:
        msg = _("The screen is locked by a system administrator.")
    if len(sys.argv) > 2:
        unlock_secs = int(sys.argv[2])
    else:
        unlock_secs = None
    LockScreen(True).lock(msg, unlock_secs)
    Gtk.main()


if __name__ == '__main__':
    main()
