#-*- coding: utf-8 -*-
import gtk
import pygtk

from epoptes import __version__

class About:
    def __init__(self):
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('about_dialog.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
        
        self.dialog = self.get('aboutdialog')
        logo = gtk.gdk.pixbuf_new_from_file_at_size(
            '../icons/hicolor/scalable/apps/epoptes.svg', 48, 48)
        self.dialog.set_logo(logo)
        self.dialog.set_version(__version__)
    
    def run(self):
        self.dialog.run()
        self.dialog.destroy()
