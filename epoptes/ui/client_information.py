#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Get client properties.
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

import gtk
import pygtk

from epoptes.common.constants import *

class ClientInformation:
    def __init__(self, selected, execute):
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('client_information.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
        self.selected = selected
        
        self.dlg = self.get('infodlg')
        self.edit_button = self.get('edit_alias_button')
        set = lambda wdg, txt: self.get(wdg).set_text(txt.strip())

        for client in selected:
            inst = client[C_INSTANCE]
            handle = inst.hsystem or client[C_SESSION_HANDLE]
            if handle:
                execute(handle, 'echo $RAM').addCallback(
                    lambda r: set('client_ram', r.strip()+' MB'))
                execute(handle, 'echo $CPU').addCallback(
                    lambda r: set('client_cpu', r))
                execute(handle, 'echo $VGA').addCallback(
                    lambda r: set('client_vga', r))
            set('client_alias', inst.alias)
            set('client_hostname', inst.hostname)
            set('client_mac', inst.mac)
            set('client_ip', handle.split(':')[0])
            set('client_type', inst.type)
            user = '--'
            if client[C_SESSION_HANDLE]:
                uname, realname = inst.users[client[C_SESSION_HANDLE]].values()
                user = uname
                if realname:
                    user += ' (%s)' %realname
            set('client_online_user', user)
            self.dlg.set_title(_('Properties of %s') %inst.get_name())
        
    def run(self):
        self.dlg.run()
        self.dlg.destroy()
        
    def on_edit_alias_clicked(self, widget):
        inst = self.selected[0][C_INSTANCE]
        edit_dlg = self.get('edit_alias_dialog')
        entry = self.get('alias_entry')
        entry.set_text(inst.alias)
        resp = edit_dlg.run()
        if resp == 1:
            inst.set_name(entry.get_text().strip())
            self.get('client_alias').set_text(inst.alias.strip())
        edit_dlg.hide()
