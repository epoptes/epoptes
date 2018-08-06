# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Execute command dialog.
"""
from epoptes.common import config
from epoptes.ui.common import locate_resource
from gi.repository import Gtk


class ExecCommand:
    """Load the dialog and settings into local variables."""
    def __init__(self, parent):
        builder = Gtk.Builder()
        builder.add_from_file(locate_resource('exec_command.ui'))
        self.dialog = builder.get_object('dlg_exec_command')
        self.dialog.set_transient_for(parent)
        self.cbt_command = builder.get_object('cbt_command')
        self.ent_command = self.cbt_command.get_child()
        self.btn_execute = builder.get_object('btn_execute')
        builder.connect_signals(self)
        for cmd in config.history:
            self.cbt_command.append_text(cmd)

    def run(self):
        """Show the dialog, then hide it so that it may be reused.
        Return the command.
        """
        reply = self.dialog.run()
        if reply == 1:
            result = self.ent_command.get_text().strip()
            if result in config.history:
                config.history.remove(result)
            config.history.insert(0, result)
            config.write_plain_file(
                config.expand_filename('history'), config.history)
        else:
            result = ''
        self.dialog.hide()

        return result

    def on_ent_command_changed(self, ent_command):
        """Enable execute only when the command is not empty."""
        self.btn_execute.set_sensitive(ent_command.get_text().strip())
