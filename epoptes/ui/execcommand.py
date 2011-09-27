#-*- coding: utf-8 -*-
import gtk
import os

# FIXME: Will epoptes use it?
filename = '/tmp/epoptes/history' # FIXME: add that to settings

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
    ex.set_flags(gtk.CAN_DEFAULT)
    dlg.set_default(ex)
    entry.set_activates_default(True)
    combo.set_model(store)
    combo.set_text_column(0)
    
    history = readCommandsHistory()
    reply = dlg.run()
    if reply == 1:
        combo = get('combobox')
        cmd = combo.child.get_text().strip()
        reply = cmd
        if cmd in history:
            history.remove(cmd)
        history.insert(0, cmd)
        writeCommandsHistory(history)
    dlg.hide()
    return reply
        
def readCommandsHistory():
    touchHistoryFile()
    f = open(filename, 'r')
    commands = f.readlines()
    f.close()
    
    combo = get('combobox')
    store.clear()
    for i in commands:
        store.append([i.strip()])
    return commands
    
def writeCommandsHistory(commands):
    f = open(filename, 'w')
    length = len(commands)
    for i in range(length): #FIXME: Use a setting for how many commands will be stored
        if i == length-1 or i == 49:
            f.write(commands[i].strip())
            break
        f.write(commands[i].strip()+'\n')
    f.close()
    readCommandsHistory()

def touchHistoryFile():
    if os.path.isfile(filename) == False:
        f = open(filename, 'w')
        f.close()
