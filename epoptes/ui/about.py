# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
About dialog.
"""
from epoptes import __version__
from epoptes.ui.common import locate_resource
from gi.repository import Gtk


class About:
    """Show an about dialog."""
    def __init__(self, parent):
        builder = Gtk.Builder()
        builder.add_from_file(locate_resource('about.ui'))
        builder.connect_signals(self)
        self.dialog = builder.get_object('dlg_about')
        self.dialog.set_transient_for(parent)
        self.dialog.set_version(__version__)

    def run(self):
        """Show the dialog, then hide it so that it may be reused."""
        self.dialog.run()
        self.dialog.hide()
