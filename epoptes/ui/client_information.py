#-*- coding: utf-8 -*-
import gtk
import pygtk

from epoptes.common.constants import *

class ClientInformation:
    def __init__(self, selected, execute):
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('client_information.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
        
        self.dlg = self.get('infodlg')
        set = lambda wdg, txt: self.get(wdg).set_text(txt.strip())

        for client in selected:
            if client[C_SYSTEM_HANDLE]:
                C_HANDLE = C_SYSTEM_HANDLE
            else:
                C_HANDLE = C_SESSION_HANDLE
            if client[C_HANDLE]:
                execute(client[C_HANDLE], 'echo $RAM').addCallback(
                    lambda r: set('client_ram', r.strip()+' MB'))
                execute(client[C_HANDLE], 'echo $CPU').addCallback(
                    lambda r: set('client_cpu', r))
                execute(client[C_HANDLE], 'echo $VGA').addCallback(
                    lambda r: set('client_vga', r))
            set('client_hostname', client[C_HOSTNAME])
            set('client_mac', client[C_MAC])
            set('client_ip', client[C_HANDLE].split(':')[0])
            set('client_type', client[C_TYPE])
            set('client_online_user', client[C_USER])
            self.dlg.set_title(_('Properties of %s') %client[C_HOSTNAME])
        
    def run(self):
        self.dlg.run()
        self.dlg.destroy()
