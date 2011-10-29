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
import random
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



## FIXME: This is dummy
def _startswith(string, pattern):
    if pattern is None:
        return True
    return string.startswith(pattern)

# Warn users to update their chroots if they have a lower epoptes-client version 
# than this
COMPATIBILITY_VERSION = [0, 1]


class EpoptesGui(object):
    
    def __init__(self, conf, host_filter):
        self.conf = conf
        self.host_filter = host_filter
        self.ltsConf = ltsconf.ltsConf()
        self.c = commands.commands()
        self.shownCompatibilityWarning = False 
        self.added = False
        self.vncserver_running = False
        self.scrWidth = 100
        self.scrHeight = 75
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
            'standalone' : self.standalone, 'server' : self.standalone}
        self.addStockImage('offline', 'images/off.png')
        self.addStockImage('online', 'images/on.png')
        self.addStockImage('users', 'images/usersgrp.png')
        self.addStockImage('system', 'images/systemgrp.png')
        
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('epoptes.ui')

        # Connect glade handlers with the callback functions
        self.wTree.connect_signals(self)
        self.get = lambda obj: self.wTree.get_object(obj)

        # Enable this when the scrollbar for the screenshot size is available
        #self.get('iconsSizeAdjustment').set_value(self.scrWidth)

        self.mainwin = self.get('mainwindow')
        
        self.cstore = gtk.ListStore(str, str, str, str, str, str, 
            gtk.gdk.Pixbuf, str, str)
        self.cview = self.get('clientsview')
        self.cView_order=(1, 0)
        self.refresh()
        
        self.cfilter = self.cstore.filter_new()
        self.cfilter.set_visible_func(self.setVisibleClients)
        self.csort = gtk.TreeModelSort(self.cfilter)
        self.cview.set_model(self.csort)
        
        
        self.cview.set_text_column(8)
        self.cview.set_pixbuf_column(6)
        self.csort.set_sort_column_id(8, gtk.SORT_ASCENDING)
        self.setClientMenuSensitivity()
        self.toggleRealNameColumn()

    #################################################################
    #                       Callback functions                      #
    #################################################################

    def refresh(self, widget=None):
        """
        Refresh clicked

        Refresh main dialog by re-loading panels containing
        lists of clients, groups and users connected.
        """
        self.ltsConf.parse()
        self.loadClients()
        self.set_cView(self.cView_order[0], self.cView_order[1])
        self.setClientMenuSensitivity()

    		
    def on_mainwin_destroy(self, widget):
        """
        Quit clicked

        Close main window
        """
        reactor.stop()
    
    
    def toggleRealNameColumn(self, widget=None):
        """Show/hide the real names of the users instead of the username"""
        pass # Implement me

    def wake_on_lan(self, widget):
        """
        For clients selected in clients' tree power them on using their
        MAC addresses
        """
        for client in self.getSelectedClients():
            # Make sure that only offline computers will be sent to wol
            if client[C_SESSION_HANDLE] == '' and client[C_SYSTEM_HANDLE] == '':
                wol.wake_on_lan(client[C_MAC])

    def poweroff(self, widget):
        """
        For clients selected in clients' tree, power them off
        """
        self.execOnSelectedClients(self.c.POWEROFF, root="auto",
            warn=self.c.POWEROFF_WARN)

    def reboot(self, widget):
        """
        For clients selected in clients' tree, reboot them
        """
        # FIXME: (Not) waiting on purpose to cause some delay to avoid 
        # any power strain.
        self.execOnSelectedClients(self.c.REBOOT, root="auto",
            warn=self.c.REBOOT_WARN)

    def logout(self, widget):
        """
        For clients selected in clients' tree, log them off
        """
        self.execOnSelectedClients(self.c.LOGOUT,
            warn=self.c.LOGOUT_WARN)
    
    ## FIXME: Don't use vinagre, we want something more integrated
    def assistStudent(self, widget, path=None, view_column=None):
        # Tell vinagre to listen for incoming connections
        subprocess.Popen(['gconftool-2', '--set',
            '/apps/vinagre/always_enable_listening', '--type', 'boolean', '1'])

        # Open vinagre
        subprocess.Popen(['vinagre'])

        # And, tell the clients to connect to the server
        self.execOnSelectedClients(self.c.EXEC +
            'x11vnc -noshm -connect_or_exit $SERVER')
    
    def monitorStudent(self, widget, path=None, view_column=None):
        # Tell vinagre to listen for incoming connections
        subprocess.Popen(['gconftool-2', '--set',
            '/apps/vinagre/always_enable_listening', '--type', 'boolean', '1'])

        # Open vinagre
        subprocess.Popen(['vinagre'])

        # And, tell the clients to connect to the server
        self.execOnSelectedClients(self.c.EXEC +
            'x11vnc -noshm -viewonly -connect_or_exit $SERVER')
    
    
    def broadcastTeacher(self, widget):
        if not self.vncserver_running:
            self.vncserver_running = True
            # TODO: switch to using -autoport
            subprocess.Popen(['x11vnc', '-noshm', '-nopw', '-quiet', '-viewonly', 
                '-shared', '-forever', '-nolookup', '-24to32', '-rfbport', '5903',
                '-allow', '127.,192.168.,10.,169.254.' ])
        self.execOnSelectedClients("""killall gnome-screensaver 2>/dev/null""")
        # TODO: don't use sleep on the direct client shell, use execute script instead
        # TODO: Move these commands maybe to commands.py #FIXME
        self.execOnSelectedClients("""test -n "$EPOPTES_VNCVIEWER_PID" && kill $EPOPTES_VNCVIEWER_PID
p=$(pidof -s ldm gdm-simple-greeter gnome-session | cut -d' ' -f1)
eval $(tr '\\0' '\\n' < /proc/$p/environ | egrep '^DISPLAY=|^XAUTHORITY=')
export DISPLAY XAUTHORITY
xset dpms force on
sleep 0.$((`hexdump -e '"%d"' -n 2 /dev/urandom` % 50 + 50))
EPOPTES_VNCVIEWER_PID=$( ./execute xvnc4viewer -Shared -ViewOnly -FullScreen -UseLocalCursor=0 -MenuKey F13 $SERVER:3)""", root=True)

    # FIXME: Make it transmission-specific, not for all transmissions
    def stopTransmissions(self, widget):
        # The clients are usually automatically killed when the server is killed
        # Unfortunately, not always, so try to kill them anyway
        self.execOnClients('test -n "$EPOPTES_VNCVIEWER_PID" && kill $EPOPTES_VNCVIEWER_PID', self.cstore, None, True)
        # TODO: remember x11vnc pid and kill it
        subprocess.Popen(['killall', 'x11vnc'])
        subprocess.Popen(['killall', '-9', 'x11vnc'])
        self.vncserver_running = False

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
        if cmd != "":# Command is 'valid', execute on selected clients 
            as_root = False
            self.execOnSelectedClients(self.c.EXEC + cmd, root=as_root)
    
    ## FIXME / FIXUS: Should we allow it?
    def openUserTerminal(self, widget):
        self.openTerminal(False)

    def openRootTerminal(self, widget):
        self.openTerminal(True)

    def remoteRootTerminal(self, widget):
        self.execOnSelectedClients("""export $(tr '\\0' '\\n' < """ +
            """/proc/$(pidof -s ldm gdm-simple-greeter gnome-session | """ +
            """cut -d' ' -f1)/environ | egrep '^DISPLAY=|^XAUTHORITY=')\n""" +
            """./execute xterm -e sudo -i""", root=True)
    ## END_FIXUS

    # FIXME : Change the way lock screen works, don't kill and relock...
    def lockScreen(self, widget):
        """
        Lock screen for all clients selected
        """
        self.execOnSelectedClients('test -n "$EPOPTES_LOCK_SCREEN_PID" && kill ' +\
            '"$EPOPTES_LOCK_SCREEN_PID"; EPOPTES_LOCK_SCREEN_PID=$(./execute '+\
            './lock-screen)')

    def unlockScreen(self, widget):
        """
        Unlock screen for all clients selected
        """
        self.execOnSelectedClients('''test -n "$EPOPTES_LOCK_SCREEN_PID" && '''+\
            '''kill "$EPOPTES_LOCK_SCREEN_PID" unset EPOPTES_LOCK_SCREEN_PID''')

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
    
    def set_cView(self, user_pos=-1, host_pos=0):
        # Save the order so all new clients get the selected format
        self.cView_order = (user_pos, host_pos)
        
        host = lambda x: self.cstore[x][C_HOSTNAME]
        user = lambda x: self.cstore[x][C_USER]
        for i in range(len(self.cstore)):
            self.cstore[i][C_VIEW_STYLE] = ''
            if user(i) == '' or user_pos == -1:
                self.cstore[i][C_VIEW_STYLE] = host(i)
            else:
                if user_pos == 0:
                    self.cstore[i][C_VIEW_STYLE] = user(i)
                    if host_pos == 1:
                        self.cstore[i][C_VIEW_STYLE] += " (%s)" %host(i)
                elif host_pos == 0:
                    self.cstore[i][C_VIEW_STYLE] = host(i)
                    if user_pos == 1:
                        self.cstore[i][C_VIEW_STYLE] += " (%s)" %user(i)
    
    
    
    def connected(self, daemon):
        self.daemon = daemon
        daemon.enumerateClients().addCallback(lambda h: self.amp_gotClients(h))

    # AMP callbacks

    def amp_clientConnected(self, handle):
        self.daemon.command(handle, u"""
            VERSION=$(dpkg-query -W -f '${Version}' epoptes-client 2>/dev/null)
            VERSION=${VERSION:-0.1}
            echo "$USER\n$HOSTNAME\n$IP\n$MAC\n$TYPE\n$UID\n$VERSION\n$$"
            """).addCallback(lambda r: self.addClient(handle, r))

    def amp_clientDisconnected(self, handle):
        for client in self.cstore:
            if client[C_SYSTEM_HANDLE] == handle:
                shutdownNotify(client[C_HOSTNAME])
                if client[C_SESSION_HANDLE] == '':
                    if self.ltsConf.sectionExists(client[C_MAC]):
                        self.savedClientReset(client)
                    else:
                        self.cstore.remove(client.iter)
                else:
                    client[C_SYSTEM_HANDLE] = ''
                break
            elif client[C_SESSION_HANDLE] == handle:
                logoutNotify(client[C_USER], client[C_HOSTNAME])
                if client[C_SYSTEM_HANDLE] == '':
                    if self.ltsConf.sectionExists(client[C_MAC]):
                        self.savedClientReset(client)
                    else:
                        self.cstore.remove(client.iter)
                else:
                    client[C_USER] = ''
                    client[C_SESSION_HANDLE] = ''
                    type = client[C_TYPE]
                    client[C_PIXBUF] = self.imagetypes[type]
                break
        self.refresh()
    

    def savedClientReset(self, client):
        client[C_SESSION_HANDLE] = ''
        client[C_SYSTEM_HANDLE] = ''
        client[C_USER] = ''
        client[C_TYPE] = 'offline'
        client[C_PIXBUF] = self.offline

    def amp_gotClients(self, handles):
        for handle in handles:
            d = self.daemon.command(handle,  u"""
                VERSION=$(dpkg-query -W -f '${Version}' epoptes-client 2>/dev/null)
                VERSION=${VERSION:-0.1}
                echo "$USER\n$HOSTNAME\n$IP\n$MAC\n$TYPE\n$UID\n$VERSION\n$$"
                """)
            d.addCallback(lambda r, h=handle: self.addClient(h, r, True))
    
    def on_button_close_clicked(self, widget):
        self.get('warningDialog').hide()

    
    # FIXME: Proofread this
    def addClient(self, handle, r, already=False):
        # already is True if the client was started before epoptes
        user, host, ip, mac, type, uid, version, pid = r.strip().split()

        # If the user logged in the client is the same as
        # the UI user, don't add the client to the iconview.
        if user == os.getenv('USER'):
            # But verify that the sysadmin isn't using the same username in all
            # standalone clients.
            try:
                for line in open('/proc/' + pid + '/environ'):
                    if 'epoptes-client' in line:
                        return
            except:
                pass
        # Do the same if there is a hostname filter specified as a parameter
        if not _startswith(host, self.host_filter):
            return
            
        # Compatibility check
        if [int(x) for x in re.split('[^0-9]*', version)] < COMPATIBILITY_VERSION:
            if not self.shownCompatibilityWarning:
                self.shownCompatibilityWarning = True
                dlg = self.get('warningDialog')
                msg = _("There was a try to connect an epoptes-client with version %s \
which is incompatible with the current epoptes version.\
\n\nYou should update your chroot.") % version
                dlg.set_property('text', msg)
                dlg.set_transient_for(self.mainwin)
                dlg.show()
            self.daemon.command(handle, u"exit")
            return
        
        
        mac = mac.upper()
        # Check if the client already exists
        index = None
        for i in range(len(self.cstore)):
            if self.cstore[i][C_IP] == ip or \
                (self.cstore[i][C_MAC] == mac and self.cstore[i][C_IP] == '') or \
                (self.cstore[i][C_HOSTNAME] == host and \
                self.cstore[i][C_IP] == '' and type == 'thin' and uid != 0):
                index = i
                entry = self.cstore[i]
                break

        # If it doesn't exist, create a new empty entry
        if index is None:
            entry = ['']*9

        
        # Check if the new client is a root epoptes-client instance or not
        if int(uid) == 0:
            entry = [host, mac, entry[C_SESSION_HANDLE], handle, type, 
                entry[C_USER], self.imagetypes[type], ip, '']
        else:
            # For standalone clients, use mac etc if not provided already
            entry = [host, entry[C_MAC], handle, entry[C_SYSTEM_HANDLE], type, 
                user, self.imagetypes[type], ip, '']
            gobject.timeout_add(5000, self.getScreenshots, 
                entry[C_SESSION_HANDLE])
            # Pop up a proper graphical notification (python-notify)
            if already:
                loggedinNotify(user, host)
            else:
                loginNotify(user, host)
        
        # If there is already an entry for this client, just update it
        # else treat this client as a new entry
        if index is not None:
            self.cstore[index] = entry
        else:
            self.cstore.append(entry)
        
        self.refresh()

    def getAllScreenshots(self):
        # TODO: Ask for screenshots for every client (Look diff at Rev:326)
        pass

    def getScreenshots(self, handle):
        # If the client can't get a screenshot, it's probably logged off,
        # so exit epoptes-client.
        exists = False
        for client in self.cstore:
            if handle == client[C_SESSION_HANDLE]:
                exists = True
                break
        if exists:
            self.execOnClients(self.c.SCREENSHOT
                % (self.scrWidth, self.scrHeight), handles=[handle], 
                    reply=self.updateScreenshots)
            return True

        return False

    def updateScreenshots(self, handle, reply):
        if reply == None:
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
                    gtk.gdk.COLORSPACE_RGB, True, 8, int(width), int(height), 
                    rowstride)
                self.cstore[i.path][C_PIXBUF] = pxb
                break
    
    # FIXME: Just shut up and fix me
    def addStockImage(self, name, filename):
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)#_at_size(filename,16,16)
        iconset = gtk.IconSet(pixbuf)

        factory = gtk.IconFactory()
        factory.add(name, iconset)
        factory.add_default()
    
    def loadClients(self):
        macs = self.ltsConf.getSavedClients()#Sections()
        for mac in macs:
            mac = mac.upper()
            exists = False
            for client in self.cstore:
                if client[C_MAC] == mac:
                    exists = True
                    break
            if not exists:
                hostname = self.ltsConf.getItem(mac, 'HOSTNAME')
                if _startswith(hostname, self.host_filter):
                    self.cstore.append([hostname, mac, '', '', 'offline', '', 
                                         self.offline, '', hostname])
    
    
    def getSelectedClients(self):
        selected = self.cview.get_selected_items()
        items = []
        for i in selected:
            path = self.cfilter.convert_path_to_child_path(
                self.csort.convert_path_to_child_path(i[0]))
            items.append(self.cstore[path])
        return items

    
    def setVisibleClients(self, model, iter):
        return True #FIXME: add a gtk.Entry to work as a filter and implement this function
    
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
        if user == None:
            user = "teacher."
        self.openLink("http://webchat.freenode.net/?nick=" + user +
            "&channels=linux.sch.gr&prompt=1")
    
    ## FIXME: We don't use this (we want to). there was a problem with twisted :-\
    def iconsSizeScaleChanged(self, widget):
        adj = self.get('iconsSizeAdjustment')
        self.scrWidth = int(adj.get_value())
        self.scrHeight = int(3*self.scrWidth/4) # Κeep the 4:3 aspect ratio
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
        clicked = widget.get_path_at_pos(int(event.x),int(event.y))

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
            
            menu.popup(None,None,None,event.button,event.time)
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
        if (clients !=[] or handles !=[]) and warning !='':
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
            elif root and client[C_SYSTEM_HANDLE] != '':
                handle = client[C_SYSTEM_HANDLE]
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
            warn=''
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
            screen_params="sudo -i"
        else:
            screen_params="-l"

        for client in clients:
            if client[C_TYPE] == 'offline':
                continue
            elif client[C_TYPE] == 'thin' and not as_root:
                server="127.0.0.1"
            else:
                server="server"

            # TODO: find unused ports instead of choosing random ones
            port = random.randint(20000, 60000)

            subprocess.Popen(['xterm', '-e', 'socat', 
                'tcp-listen:%d,keepalive=1' % port, 'stdio,raw,echo=0'])
            self.execOnClients(("""./execute sh -c "cd; sleep 1; """ +
                """TERM=xterm exec socat SYSTEM:'exec screen %s',pty,""" +
                """stderr tcp:$SERVER:%d" """) % (screen_params, port),
                [client], root=as_root)

    def execInTerminal(self, widget, command):
        name = widget.get_child().get_text()
        subprocess.Popen([ 'x-terminal-emulator', '-e', 'sh', '-c', command
            + ' && read -p "Script \'%s\' finished succesfully. Press [Enter] to close this window." dummy' %name
            + ' || read -p "Script \'%s\' finished with errors. Press [Enter] to close this window." dummy' %name]
            )

