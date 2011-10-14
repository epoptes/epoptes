#-*- coding: utf-8 -*-
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
                subprocess.Popen(['sh', '-c',
                    """'TERM=xterm socat SYSTEM:"sleep 1 && exec screen -xRR ra", \\
                    pty,stderr tcp:%s:%d & exec xterm -e screen -l -S ra'"""
                    % (ip, port)])
            else:
                subprocess.Popen(['epoptes-remote-assistance', "%s:%d" % (ip, port)])
        dlg.destroy()
