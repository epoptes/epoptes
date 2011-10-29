#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Command execution.
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
import os

from epoptes.common import config


wTree = gtk.Builder()
get = lambda obj: wTree.get_object(obj)
store = gtk.ListStore(str)

def startExecuteCmdDlg():
    wTree.add_from_file('executeCommand.ui')
    dlg = get('execDialog')
    combo = get('combobox')
    entry = combo.child
    completion = get('entrycompletion')
    entry.set_completion(completion)
    completion.set_model(store)
    ex = get('execute')
    entry.set_activates_default(True)
    combo.set_model(store)
    combo.set_text_column(0)

    combo = get('combobox')
    store.clear()
    #TODO: remove
    config.history = []
    for i in config.history:
        store.append([i.strip()])

    reply = dlg.run()
    if reply == 1:
        cmd = combo.child.get_text().strip()
        reply = cmd
        if cmd in config.history:
            config.history.remove(cmd)
        config.history.insert(0, cmd)
    dlg.hide()

    return reply
