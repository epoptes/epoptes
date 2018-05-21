#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Command execution.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
# 2018, Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from epoptes.common import config


def startExecuteCmdDlg(parent):
    """Show the execute commands dialog and return the inserted command.

    If the dialog was closed, return an empty string.
    """
    wTree = Gtk.Builder()
    get = lambda obj: wTree.get_object(obj)
    wTree.add_from_file('executeCommand.ui')
    dlg = get('execDialog')
    dlg.set_transient_for(parent)
    combo = get('combobox')
    entry = combo.get_child()
    entry.executeButton = get('execute')
    entry.connect('changed', text_changed)

    for cmd in config.history:
        combo.append_text(cmd)
    
    cmd = ''
    reply = dlg.run()
    if reply == 1:
        cmd = combo.get_child().get_text().strip()
        if cmd in config.history:
            config.history.remove(cmd)
        config.history.insert(0, cmd)
        config.write_history()
    dlg.destroy()
    
    return cmd


def text_changed(editable):
    editable.executeButton.set_sensitive(editable.get_text().strip())
