#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# GUI.
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

import pygtk
pygtk.require('2.0')

import gtk
import gobject
import os
import re
import dbus
import logging
import sys
import shlex
from gobject import TYPE_PYOBJECT as gPyobject
from twisted.internet import reactor
from twisted.python import log

from epoptes import __version__
from epoptes import ui
from notifications import *
from execcommand import *
from sendmessage import *
from about_dialog import About
from client_information import ClientInformation
from remote_assistance import RemoteAssistance
from epoptes.daemon import uiconnection
from epoptes.core.lib_users import *
from epoptes.common import commands
from epoptes.common import ltsconf
from epoptes.common import config
from epoptes.common.constants import *
from epoptes.core import wol
from epoptes.core.structs import *


class EpoptesGui(object):
    
    def __init__(self):
        self.c = commands.commands()
        self.shownCompatibilityWarning = False 
        self.added = False
        self.vncserver = None
        self.vncviewer = None
        self.scrWidth = 100
        self.scrHeight = 75
        self.current_macs = subprocess.Popen(['sh', '-c', 
        """ip -oneline -family inet link show | sed -n '/.*ether[[:space:]]*\\([[:xdigit:]:]*\).*/{s//\\1/;y/abcdef-/ABCDEF:/;p;}'"""], 
                                             stdout=subprocess.PIPE).stdout.read().split()
        if os.getuid() != 0:
            if 'thumbnails_width' in config.user:
                self.scrWidth = config.user['thumbnails_width']
            if 'thumbnails_height' in config.user:
                self.scrHeight = config.user['thumbnails_height']
        self.offline = gtk.gdk.pixbuf_new_from_file('images/offline.svg')
        self.thin = gtk.gdk.pixbuf_new_from_file('images/thin.svg')
        self.fat = gtk.gdk.pixbuf_new_from_file('images/fat.svg')
        self.standalone = gtk.gdk.pixbuf_new_from_file('images/standalone.svg')
        self.imagetypes = {'thin' : self.thin, 'fat' : self.fat,
            'standalone' : self.standalone, 'server' : self.standalone, 'offline' : self.offline}
        
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('epoptes.ui')
        
        # Connect glade handlers with the callback functions
        self.wTree.connect_signals(self)
        self.get = lambda obj: self.wTree.get_object(obj)
        
        self.gstore = gtk.ListStore(str, object)
        
        self.gtree = self.get("groups_tree")
        self.gtree.set_model(self.gstore)
        self.gtree.get_selection().connect("changed", self.on_group_selection_changed)
        
        # Enable this when the scrollbar for the screenshot size is available
        #self.get('iconsSizeAdjustment').set_value(self.scrWidth)

        self.mainwin = self.get('mainwindow')
        
        self.cstore = gtk.ListStore(str, gtk.gdk.Pixbuf, object, str)
        self.cview = self.get('clientsview')
        self.cView_order = (1, 0)
        self.set_cView(*self.cView_order)
        
        self.cview.set_model(self.cstore)
        self.cview.set_text_column(C_LABEL)
        self.cview.set_pixbuf_column(C_PIXBUF)
        self.cstore.set_sort_column_id(C_LABEL, gtk.SORT_ASCENDING)
        self.setClientMenuSensitivity()
        
        self.cview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, [("add", gtk.TARGET_SAME_APP, 0)], gtk.gdk.ACTION_COPY)
        self.gtree.enable_model_drag_dest([("add", gtk.TARGET_SAME_APP, 0)], gtk.gdk.ACTION_COPY)
        
        self.default_group = Group(_('All clients'))
        auto_iter = self.gstore.append([self.default_group.name, self.default_group])
        self.default_group.ref = gtk.TreeRowReference(self.gstore, self.gstore.get_path(auto_iter))
        self.gtree.get_selection().select_path(self.default_group.ref.get_path())
        
        saved_clients, groups = config.read_groups(os.path.expanduser('~/.config/epoptes/groups.json'))
        for grp in groups:
            self.gstore.append([grp.name, grp])
        
        self.fillIconView(self.getSelectedGroup()[1])

    #################################################################
    #                       Callback functions                      #
    #################################################################
    def on_gtree_drag_drop(self, wid, context, x, y, time):
        context.finish(True, False, time)
        
        path = self.gtree.get_path_at_pos(x, y)
        if path:
            path = path[0]
            for cln in self.getSelectedClients():
                cln = cln[C_INSTANCE]
                self.gstore[path][G_INSTANCE].add_client(cln)
        return True
    
    def on_mainwin_destroy(self, widget):
        """
        Quit clicked

        Close main window
        """
        self.gstore.remove(self.gstore.get_iter(self.default_group.ref.get_path()))
        config.save_groups(os.path.expanduser('~/.config/epoptes/groups.json'), self.gstore)
        if not self.vncserver is None:
            self.vncserver.kill()
        if not self.vncviewer is None:
            self.vncviewer.kill()
        reactor.stop()


    def toggleRealNames(self, widget=None):
        """Show/hide the real names of the users instead of the usernames"""
        pass # Implement me

    def wake_on_lan(self, widget):
        """Boot the selected computers with WOL"""
        for client in self.getSelectedClients():
            # Make sure that only offline computers will be sent to wol
            client = client[C_INSTANCE]
            if client.is_offline():
                wol.wake_on_lan(client.mac)

    def poweroff(self, widget):
        """Shut down the selected clients."""
        self.execOnSelectedClients(self.c.POWEROFF, root="auto",
            warn=self.c.POWEROFF_WARN)

    def reboot(self, widget):
        """Reboot the selected clients."""
        # FIXME: (Not) waiting on purpose to cause some delay to avoid 
        # any power strain.
        self.execOnSelectedClients(self.c.REBOOT, root="auto",
            warn=self.c.REBOOT_WARN)

    def logout(self, widget):
        """Log off the users of the selected clients."""
        self.execOnSelectedClients(self.c.LOGOUT, warn=self.c.LOGOUT_WARN)


    def reverseConnection(self, widget, path, view_column, cmd):
        # Open vncviewer in listen mode
        if self.vncviewer is None:
            self.vncviewer = subprocess.Popen(['xvnc4viewer', '-listen'])

        # And, tell the clients to connect to the server
        self.execOnSelectedClients(self.c.EXEC + cmd)


    def assistStudent(self, widget, path=None, view_column=None):
        self.reverseConnection(widget, path, view_column,
            'x11vnc -noshm -24to32 -connect_or_exit $SERVER')


    def monitorStudent(self, widget, path=None, view_column=None):
        self.reverseConnection(widget, path, view_column,
            'x11vnc -noshm -24to32 -viewonly -connect_or_exit $SERVER')


    def findUnusedPort(self, base=None):
        """Find an unused port, optionally starting from "base"."""
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if base is None:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
            s.close()
            return port
        else:
            port = int(base)
            while port < 65535:
                try:
                    s.connect(('', port))
                    s.shutdown(2)
                    port += 1
                except:
                    return port
            return None


    def broadcastTeacher(self, widget):
        if self.vncserver is None:
            self.vncport = self.findUnusedPort()
            # TODO: use a password instead of -allow
            self.vncserver = subprocess.Popen(['x11vnc', '-noshm', '-nopw',
                '-quiet', '-viewonly', '-shared', '-forever', '-nolookup',
                '-24to32', '-rfbport', str(self.vncport), '-allow',
                '127.,192.168.,10.,169.254.' ])
        self.execOnSelectedClients("""killall gnome-screensaver 2>/dev/null""")
        # TODO: don't use sleep on the direct client shell, use execute script instead
        # pgrep -x only checks the first 15 characters found in /proc/pid/stat.
        # Check the length with e.g.: x="lxdm-greeter-gtk"; echo ${x:0:15}
        # The following greeters spawn dbus-daemon, so there's no need for them
        # to be in the greeters list:
        # gdm-simple-greeter, unity-greeter
        # Unfortunately, dbus-daemon doesn't contain DBUS_SESSION_BUS_ADDRESS.
        self.execOnSelectedClients("""
test -n "$EPOPTES_VNCVIEWER_PID" && kill $EPOPTES_VNCVIEWER_PID
p=$(pgrep -nx 'ldm|kdm_greet|lxdm-greeter-gt|dbus-daemon')
export $(tr '\\0' '\\n' < /proc/$p/environ | egrep '^DISPLAY=|^XAUTHORITY=')
xset dpms force on
sleep 0.$((`hexdump -e '"%%d"' -n 2 /dev/urandom` %% 50 + 50))
EPOPTES_VNCVIEWER_PID=$(./execute xvnc4viewer -Shared -ViewOnly -FullScreen \
-UseLocalCursor=0 -MenuKey F13 $SERVER:%d)""" % self.vncport, root=True)


    def stopTransmissions(self, widget):
        # The vnc clients should automatically exit when the server is killed.
        # Unfortunately, that isn't always true, so try to kill them anyway.
        self.execOnClients("""
test -n "$EPOPTES_VNCVIEWER_PID" && kill $EPOPTES_VNCVIEWER_PID
unset EPOPTES_VNCVIEWER_PID""", self.cstore, None, True)
        if not self.vncserver is None:
            self.vncserver.kill()
            self.vncserver = None


    ## FIXME FIXME: Should we allow teacher to run whatever command in clients?
    def execDialog(self, widget):
        cmd = startExecuteCmdDlg()
        # If Cancel or Close were clicked
        if cmd == 0 or cmd == -4:
            return
        as_root = False
        if cmd[:5] == 'sudo ':
            as_root = True
            cmd = cmd[4:]
        self.execOnSelectedClients(self.c.EXEC + cmd, root=as_root)

    ## FIXME FIXME: Don't use zenity...
    def sendMessageDialog(self, widget):
        cmd = startSendMessageDlg()
        if cmd != "": # Command is 'valid', execute on selected clients 
            as_root = False
            self.execOnSelectedClients(self.c.EXEC + cmd, root=as_root)
    
    ## FIXME / FIXUS: Should we allow it?
    def openUserTerminal(self, widget):
        self.openTerminal(False)

    def openRootTerminal(self, widget):
        self.openTerminal(True)

    def remoteRootTerminal(self, widget):
        self.execOnSelectedClients("""
p=$(pgrep -nx 'ldm|kdm_greet|lxdm-greeter-gt|dbus-daemon')
export $(tr '\\0' '\\n' < /proc/$p/environ | egrep '^DISPLAY=|^XAUTHORITY=')
./execute xterm -e bash -l""", root=True)
    ## END_FIXUS

    # FIXME : Change the way lock screen works, don't kill and relock...
    def lockScreen(self, widget):
        """
        Lock screen for all clients selected
        """
        self.execOnSelectedClients('test -n "$EPOPTES_LOCK_SCREEN_PID" && kill ' + \
            '"$EPOPTES_LOCK_SCREEN_PID"; EPOPTES_LOCK_SCREEN_PID=$(./execute ' + \
            './lock-screen)')

    def unlockScreen(self, widget):
        """
        Unlock screen for all clients selected
        """
        self.execOnSelectedClients('''test -n "$EPOPTES_LOCK_SCREEN_PID" && ''' + \
            '''kill "$EPOPTES_LOCK_SCREEN_PID"; unset EPOPTES_LOCK_SCREEN_PID''')

    # FIXME: Find something better
    def soundOff(self, widget):
        """
        Disable sound usage for clients selected
        """
        self.execOnSelectedClients(self.c.EXEC_AMIXER + 'mute', root=True)

    def soundOn(self, widget):
        """
        Enable sound usage for clients selected
        """
        self.execOnSelectedClients(self.c.EXEC_AMIXER + 'unmute', root=True)
    
    def on_move_group_down_clicked(self, widget):
        pass
    
    def on_move_group_up_clicked(self, widget):
        #selected_group_iter = self.getSelectedGroup()
        #self.gstore.swap(selected_group_iter, )
        pass
        
    def on_remove_group_clicked(self, widget):
        group_iter = self.getSelectedGroup()[0]
        group = self.gstore[group_iter][G_INSTANCE]
        
        if self.warnDlgPopup(_('Are you sure you want to remove the group "%s"?') % group.name):
            self.gstore.remove(group_iter)
            
    def on_add_group_clicked(self, widget):
        cell = self.get('cellrenderertext1')
        cell.set_property('editable', True)
        new_group = Group()
        iter = self.gstore.append([new_group.name, new_group])
        # Edit the name of the newly created group
        self.gtree.set_cursor(self.gstore.get_path(iter), self.get('group_name_column'), True)
    
    def on_group_renamed(self, widget, path, new_name):
        self.gstore[path][G_LABEL] = new_name
        self.gstore[path][G_INSTANCE].name = new_name
        
    #FIXME: Remove the second parameter, find a better way
    def on_tb_client_properties_clicked(self, widget=None):
        ClientInformation(self.getSelectedClients(), self.daemon.command).run()
    
    def on_mi_remote_assistance_activate(self, widget=None):
        RemoteAssistance().run()
    
    def on_mi_about_activate(self, widget=None):
        About().run()
        
    def on_cViewHU_toggled(self, mitem):
        self.set_cView(1, 0)
    
    def on_cViewUH_toggled(self, mitem):
        self.set_cView(0, 1)
    
    def on_cViewH_toggled(self, mitem):
        self.set_cView(-1, 0)
    
    def on_cViewU_toggled(self, mitem):
        self.set_cView(0, -1)
    
    def set_cView(self, user_pos= -1, name_pos=0):
        # Save the order so all new clients get the selected format
        self.cView_order = (user_pos, name_pos)
        for row in self.cstore:            
            self.setLabel(row)
    
    def connected(self, daemon):
        self.daemon = daemon
        daemon.enumerateClients().addCallback(lambda h: self.amp_gotClients(h))

    # AMP callbacks
    def amp_clientConnected(self, handle):
        print "New connection from", handle
        self.daemon.command(handle, u"""
            VERSION=$(dpkg-query -W -f '${Version}' epoptes-client 2>/dev/null)
            VERSION=${VERSION:-0.1}
            echo "$USER\n$HOSTNAME\n$IP\n$MAC\n$TYPE\n$UID\n$VERSION\n$$"
            """).addCallback(lambda r: self.addClient(handle, r))

    def amp_clientDisconnected(self, handle):
        print "Disconnect from", handle
        
        def determine_offline(client):
            if client.hsystem == '' and client.users == {}:
                client.set_offline()
        
        for client in clients:
            if client.hsystem == handle:
                if self.getSelectedGroup()[1].has_client(client) or self.isDefaultGroupSelected():
                    shutdownNotify(client.get_name())
                client.hsystem = ''
                determine_offline(client)
                break
            
            elif handle in client.users:
                if self.getSelectedGroup()[1].has_client(client) or self.isDefaultGroupSelected():
                    logoutNotify(client.users[handle], client.get_name())
                del client.users[handle]
                determine_offline(client)
                break
        self.fillIconView(self.getSelectedGroup()[1])
    
    def savedClientReset(self, client):
        inst = client[C_INSTANCE]
        inst.hsession = inst.hsystem = inst.user = ''
        inst.type = 'offline'
        client[C_PIXBUF] = self.offline

    def amp_gotClients(self, handles):
        print "Got clients:", ', '.join(handles) or 'None'
        for handle in handles:
            d = self.daemon.command(handle, u"""
                VERSION=$(dpkg-query -W -f '${Version}' epoptes-client 2>/dev/null)
                VERSION=${VERSION:-0.1}
                echo "$USER\n$HOSTNAME\n$IP\n$MAC\n$TYPE\n$UID\n$VERSION\n$$"
                """)
            d.addCallback(lambda r, h=handle: self.addClient(h, r, True))
    
    def on_button_close_clicked(self, widget):
        self.get('warningDialog').hide()
    
    def on_group_selection_changed(self, treeselection):
        self.cstore.clear()
        selected = self.getSelectedGroup()
        
        if selected is not None:
            self.fillIconView(selected[1])
        else:
            if not self.default_group.ref.valid():
                return
            self.gtree.get_selection().select_path(self.default_group.ref.get_path())
        self.get('remove_group').set_sensitive(not self.isDefaultGroupSelected())
    
    def addToIconView(self, client):
        """Properly add a Client class instance to the clients iconview."""
        # If there are one or more users on client, add a new iconview entry
        # for each one of them.
        if client.users:
            for hsession, user in client.users.iteritems():
                self.cstore.append([self.calculateLabel(client, user), self.imagetypes[client.type], client, hsession])
                self.getScreenshots(hsession)
        else:
            self.cstore.append([self.calculateLabel(client), self.imagetypes[client.type], client, ''])
    
    def fillIconView(self, group):
        """Fill the clients iconview from a Group class instance."""
        self.cstore.clear()
        if self.isDefaultGroupSelected():
            clients_list = [client for client in clients if client.type != 'offline']
        else:
            clients_list = group.get_members()
        # Add the new clients to the iconview
        for client in clients_list:
            self.addToIconView(client)
    
    def isDefaultGroupSelected(self):
        """Return True if the default group is selected"""
        return self.getSelectedGroup()[1] is self.default_group
    
    def getSelectedGroup(self):
        """Return a 2-tuple containing the iter and the instance
        for the currently selected group."""
        iter = self.gtree.get_selection().get_selected()[1]
        if iter:
            return (iter, self.gstore[iter][G_INSTANCE])
        else:
            return None
        
    def addClient(self, handle, r, already=False):
        # already is True if the client was started before epoptes
        user, host, ip, mac, type, uid, version, pid = r.strip().split()
        print "---\n**addClient's been called for", handle
        
        # Check if the incoming client is the same with the computer in which
        # epoptes is running, so we don't add it to the list.
        # FIXME FiXME: Both ifs don't work for root clients that run in the same
        # computer as epoptes
        if mac in self.current_macs:
            print "* Won't add this client to my lists"
            return False
        
        print '  Continuing inside addClient...'
        
        # Compatibility check
        if [int(x) for x in re.split('[^0-9]*', version)] < COMPATIBILITY_VERSION:
            if not self.shownCompatibilityWarning:
                self.shownCompatibilityWarning = True
                dlg = self.get('warningDialog')
                # Show different messages for LTSP clients and standalones.
                msg = _("There was a try to connect an epoptes-client with version %s \
which is incompatible with the current epoptes version.\
\n\nYou should update your chroot.") % version
                dlg.set_property('text', msg)
                dlg.set_transient_for(self.mainwin)
                dlg.show()
            self.daemon.command(handle, u"exit")
            return False
        
        client = None
        for inst in clients:
            # Find if the new handle is a known client
            if mac == inst.mac:
                client = inst
                print '* This is an existing client'
                break
        if client is None:
            print '* This client is a new one, creating an instance'
            client = Client(mac=mac)
            
        # Update/fill the client information
        client.type, client.hostname = type, host
        if int(uid) == 0:
            # This is a root epoptes-client
            print '* I am a root client'
            client.hsystem = handle
        else:
            # This is a user epoptes-client
            print '* I am a user client, will add', user, 'in my list'
            client.add_user(user, handle)
            if not already and (self.getSelectedGroup()[1].has_client(client) or self.isDefaultGroupSelected()):
                loginNotify(user, host)
        
        self.fillIconView(self.getSelectedGroup()[1])
    
    def setLabel(self, row):
        inst = row[C_INSTANCE]
        if row[C_SESSION_HANDLE]:            
            user = row[C_INSTANCE].users[row[C_SESSION_HANDLE]]
        else:
            user = ''
        row[C_LABEL] = self.calculateLabel(inst, user)

    
    
    
    def calculateLabel(self, client, username=''):
        """Return the iconview label from a hostname/alias
        and a username, according to the user options.
        """
        user_pos, name_pos = self.cView_order
        
        if client.get_name() == '':
            return client.mac
        
        alias = client.get_name()
        if username == '' or user_pos == -1:
            return alias
        else:
            if user_pos == 0:
                label = username
                if name_pos == 1:
                    label += " (%s)" % alias
            elif name_pos == 0:
                label = alias
                if user_pos == 1:
                    label += " (%s)" % username
            return label
    
    def getAllScreenshots(self):
        # TODO: Ask for screenshots for every client (Look diff at Rev:326)
        pass

    def getScreenshots(self, handle):
        # TODO: Implement this using gtk.TreeRowReferences instead
        # of searching the whole model (Need to modify execOnClients)
        for client in self.cstore:
            if handle == client[C_SESSION_HANDLE]:
                self.execOnClients(self.c.SCREENSHOT
                    % (self.scrWidth, self.scrHeight), handles=[handle],
                        reply=self.updateScreenshots)
                return


    def updateScreenshots(self, handle, reply):
        if not reply:
            return
        try:
            rowstride, size, pixels = reply.strip().split('\n', 2)
        except:
            return
        rowstride = int(rowstride)
        width, height = size.split('x')
        for i in self.cstore:
            if handle == i[C_SESSION_HANDLE]:
                pxb = gtk.gdk.pixbuf_new_from_data(pixels,
                    gtk.gdk.COLORSPACE_RGB, False, 8, int(width), int(height),
                    rowstride)
                self.cstore[i.path][C_PIXBUF] = pxb
                # We want to ask for thumbnails every 5 sec after the last one.
                # So if the client is too stressed and needs 7 secs to
                # send a thumbnail, we'll ask for one every 12 secs.
                # TODO: check if there are cases where we want to continue
                # asking for screenshots even if we got an empty/broken one.
                gobject.timeout_add(5000, self.getScreenshots, handle)
                break
    
    def getSelectedClients(self):
        selected = self.cview.get_selected_items()
        items = []
        for i in selected:
            items.append(self.cstore[i])
        return items
        
    def changeHostname(self, mac, new_name):
        pass #FIXME: Implement this (virtual hostname)
    
    def openLink(self, link):
        subprocess.Popen(["xdg-open", link])

    def openHelpLink(self, widget):
        self.openLink("http://epoptes.sourceforge.net")

    def openBugsLink(self, widget):
        self.openLink("https://bugs.launchpad.net/epoptes")

    def openQuestionsLink(self, widget):
        self.openLink("https://answers.launchpad.net/epoptes")

    ## TODO: fix the links, and replace the forum link with a translations link
    def openForumLink(self, widget):
        self.openLink("http://alkisg.mysch.gr/steki/index.php?board=67.0")

    def openIRCLink(self, widget):
        user = os.getenv("USER")
        if user is None:
            user = "teacher."
        self.openLink("http://webchat.freenode.net/?nick=" + user + 
            "&channels=linux.sch.gr&prompt=1")
    
    ## FIXME: We don't use this (we want to). there was a problem with twisted :-\
    def iconsSizeScaleChanged(self, widget):
        adj = self.get('iconsSizeAdjustment')
        self.scrWidth = int(adj.get_value())
        self.scrHeight = int(3 * self.scrWidth / 4) # Κeep the 4:3 aspect ratio
        self.getAllScreenshots()

    def scrIncreaseSize(self, widget):
        # Increase the size of screenshots by 2 pixels in width
        adj = self.get('iconsSizeAdjustment')
        adj.set_value(adj.get_value() + 2)

    def scrDecreaseSize(self, widget):
        # Decrease the size of screenshots by 2 pixels in width
        adj = self.get('iconsSizeAdjustment')
        adj.set_value(adj.get_value() - 2)
    
    ## END_FIXME

    def contextMenuPopup(self, widget, event):
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))

        if event.button == 3:
            if widget is self.cview:
                selection = widget
                selected = widget.get_selected_items()
            else:
                selection = widget.get_selection()
                selected = selection.get_selected_rows()[1]
                if clicked:
                    clicked = clicked[0]

            if clicked:
                if not clicked in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()

            if widget is self.cview:
                menu = self.get('clients').get_submenu()
            
            menu.popup(None, None, None, event.button, event.time)
            menu.show()
            return True

    def setClientMenuSensitivity(self, widget=None):
        selected = self.getSelectedClients()
        sensitive = False
        if len(selected) == 1:
            sensitive = True
        self.get('miClientProperties').set_sensitive(sensitive)
        self.get('tb_client_properties').set_sensitive(sensitive)

    
    ## FIXME: This is not yet finished, implement it
    def editClientName(self, widget):

        dlg = self.get('entrydialog')
        entry = self.get('newhostname')
        if widget is self.get('change_name'):
            hostname = self.get('client_name').get_text()
            mac = self.get('client_mac').get_text()
            entry.set_text(hostname)
        resp = dlg.run()
        dlg.hide()
        if resp == 1:
            self.refresh()
            print "No changes made, not yet implemented"
            
    ## END_FIXME

    
    ## FIXME / FIXUS: Proofread this (root etc...)
    def execOnClients(self, command, clients=[], reply=None, root=False,
                        handles=[], warning=''):
        '''reply should be a method in which the result will be sent'''
        
        if len(self.cstore) == 0:
            # print 'No clients'
            return False
        if (clients != [] or handles != []) and warning != '':
            if self.warnDlgPopup(warning) == False:
                return
        if clients == [] and handles != []:
            for handle in handles:
                cmd = self.daemon.command(handle, unicode(command))
                cmd.addErrback(self.printErrors)
                if reply:
                    cmd.addCallback(lambda re, h=handle: reply(h, re))
        for client in clients:
            if (root == "auto" or not root) and client[C_SESSION_HANDLE] != '':
                handle = client[C_SESSION_HANDLE]
            elif root and client[C_INSTANCE].hsystem != '':
                handle = client[C_INSTANCE].hsystem
            else:
                continue
            cmd = self.daemon.command(handle, unicode(command))
            cmd.addErrback(self.printErrors)
            if reply:
                cmd.addCallback(lambda re, h=handle: reply(h, re))

    def execOnSelectedClients(self, command, reply=None, root=False, warn=''):
        clients = self.getSelectedClients()
        if len(clients) == 0: # No client selected, send the command to all
            clients = self.cstore
        else: # Show the warning only when no clients are selected
            warn = ''
        self.execOnClients(command, clients, reply, root, warning=warn)
    
    # END_FIXUS

    def warnDlgPopup(self, warning):
        dlg = self.get('executionwarning')
        dlg.set_property('text', warning)
        resp = dlg.run()
        dlg.set_property('text', '')
        dlg.hide()
        # -8 is the response id of the "Yes" button (-9 for the "No")
        if resp == -8:
            return True
        else:
            return False

    
    ## FIXME/ DELETEME??
    def printErrors(self, error):
        print 'ErrorCallback:', error
        return

    def openTerminal(self, as_root):
        clients = self.getSelectedClients()
        
        # If there is no client selected, send the command to all
        if len(clients) == 0:
            clients = self.cstore

        if as_root:
            screen_params = "bash -l"
        else:
            screen_params = "-l"

        for client in clients:
            inst = client[C_INSTANCE]
            if inst.type == 'offline':
                continue
            elif inst.type == 'thin' and not as_root:
                server = "127.0.0.1"
            else:
                server = "server"

            port = self.findUnusedPort()

            subprocess.Popen(['xterm', '-e', 'socat',
                'tcp-listen:%d,keepalive=1' % port, 'stdio,raw,echo=0'])
            self.execOnClients(("""./execute sh -c "cd; sleep 1; """ + 
                """TERM=xterm exec socat SYSTEM:'exec screen %s',pty,""" + 
                """stderr tcp:$SERVER:%d" """) % (screen_params, port),
                [client], root=as_root)

    def execInTerminal(self, widget, command):
        name = widget.get_child().get_text()
        subprocess.Popen([ 'x-terminal-emulator', '-e', 'sh', '-c', command
            + ' && read -p "Script \'%s\' finished succesfully. Press [Enter] to close this window." dummy' % name
            + ' || read -p "Script \'%s\' finished with errors. Press [Enter] to close this window." dummy' % name]
            )

