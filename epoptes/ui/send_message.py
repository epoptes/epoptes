# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Send message dialog.
"""
import os

from epoptes.common import config, locate_resource
from gi.repository import Gtk


class SendMessage:
    """Load the dialog and settings into local variables."""
    def __init__(self, parent):
        builder = Gtk.Builder()
        builder.add_from_file(locate_resource('send_message.ui'))
        self.dialog = builder.get_object('dlg_send_message')
        self.dialog.set_transient_for(parent)
        self.txv_message = builder.get_object('txv_message')
        self.ent_title = builder.get_object('ent_title')
        self.ent_title.set_text(
            config.settings.get('GUI', 'messages_default_title'))
        self.chb_markup = builder.get_object('chb_markup')
        self.chb_markup.set_active(
            config.settings.getboolean('GUI', 'messages_use_markup'))

    def run(self):
        """Show the dialog, then hide it so that it may be reused.
        Return (text, title, markup).
        """
        reply = self.dialog.run()
        if reply == 1:
            text = self.txv_message.get_buffer().props.text
            title = self.ent_title.get_text().strip()
            use_markup = self.chb_markup.get_active()
            result = (text, title, use_markup)
            config.settings.set('GUI', 'messages_default_title', title)
            config.settings.set('GUI', 'messages_use_markup', str(use_markup))
            # TODO: move this to config.py
            fset = open(os.path.expanduser('~/.config/epoptes/settings'), 'w')
            config.settings.write(fset)
            fset.close()
        else:
            result = ()
        self.dialog.hide()

        return result
