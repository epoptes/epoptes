# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Client information dialog.
"""
from epoptes.common import gettext as _, locate_resource
from epoptes.common.constants import C_INSTANCE, C_SESSION_HANDLE
from gi.repository import Gtk


class ClientInformation:
    """Load the dialog and settings into local variables."""
    def __init__(self, parent):
        builder = Gtk.Builder()
        builder.add_from_file(locate_resource('client_information.ui'))
        builder.connect_signals(self)
        self.dialog = builder.get_object('dlg_client_information')
        self.dialog.set_transient_for(parent)
        self.btn_edit_alias = builder.get_object('btn_edit_alias')
        self.dlg_edit_alias = builder.get_object('dlg_edit_alias')
        self.ent_alias = builder.get_object('ent_alias')
        self.lbl_type = builder.get_object('lbl_type')
        self.lbl_alias = builder.get_object('lbl_alias')
        self.lbl_hostname = builder.get_object('lbl_hostname')
        self.lbl_mac = builder.get_object('lbl_mac')
        self.lbl_ip = builder.get_object('lbl_ip')
        self.lbl_user = builder.get_object('lbl_user')
        self.lbl_cpu = builder.get_object('lbl_cpu')
        self.lbl_ram = builder.get_object('lbl_ram')
        self.lbl_vga = builder.get_object('lbl_vga')
        self.client = None

    def run(self, client, execute):
        """Show the dialog, then hide it so that it may be reused."""
        self.client = client

        inst = client[C_INSTANCE]
        handle = inst.hsystem or client[C_SESSION_HANDLE]

        self.lbl_type.set_text(inst.type)
        self.lbl_alias.set_text(inst.alias)
        self.lbl_hostname.set_text(inst.hostname)
        self.lbl_mac.set_text(inst.mac)
        self.lbl_ip.set_text(handle.split(':')[0])
        if client[C_SESSION_HANDLE]:
            uname, realname = inst.users[client[C_SESSION_HANDLE]].values()
            if realname:
                user = '{} ({})'.format(uname, realname)
            else:
                user = uname
        else:
            user = ''
        self.lbl_user.set_text(user)
        self.lbl_cpu.set_text('')
        self.lbl_ram.set_text('')
        self.lbl_vga.set_text('')
        if handle:
            execute(handle, 'echo "$CPU"').addCallback(
                self.cb_set_text, self.lbl_cpu)
            execute(handle, 'echo "$RAM MiB"').addCallback(
                self.cb_set_text, self.lbl_ram)
            execute(handle, 'echo "$VGA"').addCallback(
                self.cb_set_text, self.lbl_vga)
        # TODO: consider new string formatting vs updating translations
        self.dialog.set_title(_('Properties of %s') % inst.get_name())
        self.dialog.run()
        self.dialog.hide()

    @staticmethod
    def cb_set_text(result, widget):
        """Set a widget text to the result of a twisted call."""
        widget.set_text(result.decode().strip())

    def on_edit_alias_clicked(self, _widget):
        """Show a dialog to edit the alias."""
        inst = self.client[C_INSTANCE]
        self.ent_alias.set_text(inst.alias)
        reply = self.dlg_edit_alias.run()
        if reply == 1:
            inst.set_name(self.ent_alias.get_text().strip())
            self.lbl_alias.set_text(inst.alias.strip())
        self.dlg_edit_alias.hide()
