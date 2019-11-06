#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2012-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Display a simple window with a message.
"""
import os
import sys

from _common import gettext as _
from gi.repository import Gtk


class MessageWindow(Gtk.Window):
    """Display a simple window with a message."""
    def __init__(self, text, title="Epoptes", markup=True,
                 icon_name="dialog-information"):
        super().__init__(title=title, icon_name=icon_name)
        self.set_position(Gtk.WindowPosition.CENTER)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        self.add(grid)

        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        grid.add(image)

        # Always load the plain text first in case the markup parsing fails
        label = Gtk.Label(
            label=text, selectable=True, hexpand=True, vexpand=True,
            halign=Gtk.Align.START, valign=Gtk.Align.START)
        if markup:
            label.set_markup(text)
        grid.add(label)

        button = Gtk.Button.new_from_stock(Gtk.STOCK_CLOSE)
        button.set_hexpand(False)
        button.set_halign(Gtk.Align.END)
        button.connect("clicked", Gtk.main_quit)
        grid.attach(button, 1, 1, 2, 1)
        self.set_focus_child(button)

        accelgroup = Gtk.AccelGroup()
        key, modifier = Gtk.accelerator_parse('Escape')
        accelgroup.connect(
            key, modifier, Gtk.AccelFlags.VISIBLE, Gtk.main_quit)
        self.add_accel_group(accelgroup)


def main():
    """Run the module from the command line."""
    if len(sys.argv) <= 1 or len(sys.argv) > 5:
        print(_("Usage: {} text [title] [markup] [icon_name]").format(
            os.path.basename(__file__)), file=sys.stderr)
        exit(1)
    text = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2]:
        title = sys.argv[2]
    else:
        title = "Epoptes"
    if len(sys.argv) > 3 and sys.argv[3]:
        markup = sys.argv[3].lower() == "true"
    else:
        markup = True
    if len(sys.argv) > 4:
        icon_name = sys.argv[4]
    else:
        icon_name = "dialog-information"

    window = MessageWindow(text, title, markup, icon_name)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
