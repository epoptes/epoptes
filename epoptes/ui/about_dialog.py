#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# About dialog.
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

from epoptes import __version__

class About:
    def __init__(self):
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('about_dialog.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
        
        self.dialog = self.get('aboutdialog')
        logo = gtk.gdk.pixbuf_new_from_file_at_size(
            '../icons/hicolor/scalable/apps/epoptes.svg', 64, 64)
        self.dialog.set_logo(logo)
        self.dialog.set_version(__version__)
        self.dialog.set_translator_credits(_("translator-credits"))
        self.dialog.set_artists(["Andrew Wedderburn (application icon)"])
    
    def run(self):
        self.dialog.run()
        self.dialog.destroy()
