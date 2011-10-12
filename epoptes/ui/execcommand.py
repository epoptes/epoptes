#-*- coding: utf-8 -*-
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
