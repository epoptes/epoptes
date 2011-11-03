#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Remote assistance.
#
# Copyright (C) 2010 Alkis Georgopoulos <alkisg@gmail.com>
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
import subprocess

class RemoteAssistance:
    def __init__(self):
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('remote_assistance.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
    
    def run(self):    
        dlg = self.get('remote_assistance_dialog')
        if self.get('sb_assist_port').get_value() == 0:
            self.get('sb_assist_port').set_value(5500)
        reply = dlg.run()
        if reply == 1:
            ip = self.get('rem_assist_ip').get_text().strip()
            port = self.get('sb_assist_port').get_value()
            if self.get('cb_assist_type').get_active() == 1:
                # Unfortunately double quoting is needed when a parameter 
                # contains spaces. That might change in the future, 
                # see http://www.sudo.ws/sudo/bugs/show_bug.cgi?id=413
                # Fortunately, sh -c 'ls' works even if the quotes there are 
                # wrong. :)
                subprocess.Popen(['sh', '-c', ("""TERM=xterm socat """ +
                    """SYSTEM:"sleep 1; exec screen -xRR ra",pty,stderr """ +
                    """tcp:%s:%d & exec xterm -e screen -l -S ra""") %
                    (ip, port)])
            else:
                subprocess.Popen(['./epoptes-remote-assistance', "%s:%d" % (ip, port)])
        dlg.destroy()
