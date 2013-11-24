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
import pipes
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
from epoptes.daemon import uiconnection
from epoptes.core.lib_users import *
from epoptes.common import ltsconf
from epoptes.common import config
from epoptes.common.constants import *
from epoptes.core import wol
from epoptes.core import structs


class EpoptesGui(object):
    
    def __init__(self):
        self.shownCompatibilityWarning = False
        self.vncserver = None
        self.vncviewer = None
        self.scrWidth = 100
        self.scrHeight = 75
        self.showRealNames = False
        self.currentScreenshots = dict()
        self.current_macs = subprocess.Popen(['sh', '-c',
            """ip -oneline -family inet link show | sed -n '/.*ether[[:space:]]*\\([[:xdigit:]:]*\).*/{s//\\1/;y/abcdef-/ABCDEF:/;p;}'
            echo $LTSP_CLIENT_MAC"""],
            stdout=subprocess.PIPE).communicate()[0].split()
        self.uid = os.getuid()
        if 'thumbnails_width' in config.user:
            self.scrWidth = config.user['thumbnails_width']
        self.offline = gtk.gdk.pixbuf_new_from_file('images/offline.svg')
        self.thin = gtk.gdk.pixbuf_new_from_file('images/thin.svg')
        self.fat = gtk.gdk.pixbuf_new_from_file('images/fat.svg')
        self.standalone = gtk.gdk.pixbuf_new_from_file('images/standalone.svg')
        self.imagetypes = {'thin' : self.thin, 'fat' : self.fat,
            'standalone' : self.standalone, 'offline' : self.offline}
        
        self.wTree = gtk.Builder()
        self.wTree.add_from_file('epoptes.ui')
        
        self.get = lambda obj: self.wTree.get_object(obj)
        
        # Connect glade handlers with the callback functions
        self.wTree.connect_signals(self)
        
        
        # Hide the remote assistance menuitem if epoptes-client is not installed
        if not os.path.isfile('/usr/share/epoptes-client/remote-assistance'):
            self.get('mi_remote_assistance').set_property('visible', False)
            self.get('remote_assistance_separator').set_property('visible', False)
        
        self.gstore = gtk.ListStore(str, object, bool)
        
        self.gtree = self.get("groups_tree")
        self.gtree.set_model(self.gstore)
        self.gtree.get_selection().connect("changed", self.on_group_selection_changed)
        
        self.mainwin = self.get('mainwindow')
        
        self.cstore = gtk.ListStore(str, gtk.gdk.Pixbuf, object, str)
        self.cview = self.get('clientsview')
        self.cView_order = (1, 0)
        self.set_cView(*self.cView_order)
        
        self.cview.set_model(self.cstore)
        self.cview.set_pixbuf_column(C_PIXBUF)
        self.cview.set_text_column(C_LABEL)
        
        self.cstore.set_sort_column_id(C_LABEL, gtk.SORT_ASCENDING)
        self.on_clients_selection_changed()
        
        self.cview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, [("add", gtk.TARGET_SAME_APP, 0)], gtk.gdk.ACTION_COPY)
        self.gtree.enable_model_drag_dest([("add", gtk.TARGET_SAME_APP, 0)], gtk.gdk.ACTION_COPY)
        
        self.default_group = structs.Group('<b>'+_('Detected clients')+'</b>')
        default_iter = self.gstore.append([self.default_group.name, self.default_group, False])
        self.default_group.ref = gtk.TreeRowReference(self.gstore, self.gstore.get_path(default_iter))
        self.gtree.get_selection().select_path(self.default_group.ref.get_path())
        
        self.get('iconsSizeAdjustment').set_value(self.scrWidth)
        self.reload_imagetypes()
        
        saved_clients, groups = config.read_groups(os.path.expanduser('~/.config/epoptes/groups.json'))
        for grp in groups:
            self.gstore.append([grp.name, grp, True])
        
        self.fillIconView(self.getSelectedGroup()[1])
        if config.settings.has_option('GUI', 'selected_group'):
            path = config.settings.getint('GUI', 'selected_group')
            self.gtree.get_selection().select_path(path)
        if config.settings.has_option('GUI', 'label'):
            try:
                self.get(config.settings.get('GUI', 'label')).set_active(True)
            except:
                pass
        if config.settings.has_option('GUI', 'showRealNames'):
            self.get('mcShowRealNames').set_active(config.settings.getboolean('GUI', 'showRealNames'))
        

    #################################################################
    #                       Callback functions                      #
    #################################################################
    def on_gtree_drag_motion(self, widget, context, x, y, etime):
        drag_info = widget.get_dest_row_at_pos(x, y)
        # Don't allow dropping in the empty space of the treeview,
        # or inside the 'Detected' group, or inside the currently selected group
        selected_path = self.gstore.get_path(self.getSelectedGroup()[0])
        if (not drag_info or drag_info[0] == self.default_group.ref.get_path() or
            drag_info[0] == selected_path):
            widget.set_drag_dest_row(None, gtk.TREE_VIEW_DROP_AFTER)
        else:
            path, pos = drag_info
            # Don't allow dropping between the groups treeview rows
            if pos == gtk.TREE_VIEW_DROP_BEFORE:
                widget.set_drag_dest_row(path, gtk.TREE_VIEW_DROP_INTO_OR_BEFORE)
            elif pos == gtk.TREE_VIEW_DROP_AFTER:
                widget.set_drag_dest_row(path, gtk.TREE_VIEW_DROP_INTO_OR_AFTER)
        
        context.drag_status(context.suggested_action, etime)
        return True
    
    def on_gtree_drag_drop(self, wid, context, x, y, time):
        dest = self.gtree.get_dest_row_at_pos(x, y)
        if dest is not None:
            path, pos = dest
            group = self.gstore[path][G_INSTANCE]
            if not group is self.default_group:
                for cln in self.getSelectedClients():
                    cln = cln[C_INSTANCE]
                    if not group.has_client(cln):
                        group.add_client(cln)
    
        context.finish(True, False, time)
        return True

    def on_mainwin_destroy(self, widget):
        """
        Quit clicked

        Close main window
        """
        sel_group = self.gstore.get_path(self.getSelectedGroup()[0])[0]
        self.gstore.remove(self.gstore.get_iter(self.default_group.ref.get_path()))
        config.save_groups(os.path.expanduser('~/.config/epoptes/groups.json'), self.gstore)
        settings = config.settings
        if not settings.has_section('GUI'):
            settings.add_section('GUI')        
        
        settings.set('GUI', 'selected_group', sel_group)
        settings.set('GUI', 'showRealNames', self.showRealNames)
        settings.set('GUI', 'thumbnails_width', self.scrWidth)
        try:
            f = open(os.path.expanduser('~/.config/epoptes/settings'), 'w')
            settings.write(f)
            f.close()
        except:
            pass
        if not self.vncserver is None:
            self.vncserver.kill()
        if not self.vncviewer is None:
            self.vncviewer.kill()
        reactor.stop()
            
    def toggleRealNames(self, widget=None):
        """Show/hide the real names of the users instead of the usernames"""
        self.showRealNames = widget.get_active()
        for row in self.cstore:            
            self.setLabel(row)

    def wake_on_lan(self, widget):
        """Boot the selected computers with WOL"""
        for client in self.getSelectedClients():
            # Make sure that only offline computers will be sent to wol
            client = client[C_INSTANCE]
            if client.is_offline():
                wol.wake_on_lan(client.mac)

    def poweroff(self, widget):
        """Shut down the selected clients."""
        self.execOnSelectedClients(["shutdown"],
            warn=_('Are you sure you want to shutdown all the computers?'))

    def reboot(self, widget):
        """Reboot the selected clients."""
        self.execOnSelectedClients(["reboot"],
            warn=_('Are you sure you want to reboot all the computers?'))


    def logout(self, widget):
        """Log off the users of the selected clients."""
        self.execOnSelectedClients(['logout'], mode=EM_SESSION,
            warn=_('Are you sure you want to log off all the users?'))


    def reverseConnection(self, widget, path, view_column, cmd, *args):
        # Open vncviewer in listen mode
        if self.vncviewer is None:
            self.vncviewerport = self.findUnusedPort()
            # If the user installed ssvnc, prefer it over xvnc4viewer
            if os.path.isfile('/usr/bin/ssvncviewer'):
                self.vncviewer = subprocess.Popen(['ssvncviewer',
                    '-multilisten', str(self.vncviewerport-5500)])
            elif os.path.isfile('/usr/bin/xvnc4viewer'):
                self.vncviewer = subprocess.Popen(['xvnc4viewer',
                    '-listen', str(self.vncviewerport)])
            else:
                self.vncviewer = subprocess.Popen(['vncviewer',
                    '-listen', str(self.vncviewerport-5500)])

        # And, tell the clients to connect to the server
        self.execOnSelectedClients([cmd, self.vncviewerport] + list(args))


    def assistUser(self, widget, path=None, view_column=None):
        if config.settings.has_option('GUI', 'grabkbdptr'):
            grab = config.settings.getboolean('GUI', 'grabkbdptr')
        if grab:
            self.reverseConnection(widget, path, view_column, 'get_assisted', 'True')
        else:
            self.reverseConnection(widget, path, view_column, 'get_assisted')


    def monitorUser(self, widget, path=None, view_column=None):
        self.reverseConnection(widget, path, view_column, 'get_monitored')


    def findUnusedPort(self):
        """Find an unused port."""
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port


    def _broadcastScreen(self, fullscreen=''):
        if self.vncserver is None:
            import random
            import string
            pwdfile=os.path.expanduser('~/.config/epoptes/vncpasswd')
            pwd=''.join(random.sample(string.letters + string.digits, 8))
            subprocess.call(['x11vnc', '-storepasswd', pwd, pwdfile])
            f=open(pwdfile)
            pwd=f.read()
            f.close()
            self.pwd=''.join('\\%o' % ord(c) for c in pwd)
            self.vncserverport = self.findUnusedPort()
            self.vncserver = subprocess.Popen(['x11vnc', '-noshm', '-nopw',
                '-quiet', '-viewonly', '-shared', '-forever', '-nolookup',
                '-24to32', '-threads', '-rfbport', str(self.vncserverport),
                '-rfbauth', pwdfile])
        self.execOnSelectedClients(['stop_screensaver'],
            mode=EM_SYSTEM_AND_SESSION)
        self.execOnSelectedClients(["receive_broadcast", self.vncserverport, 
            self.pwd, fullscreen], mode=EM_SYSTEM_OR_SESSION)


    def broadcastScreen(self, widget):
        self._broadcastScreen('true')


    def broadcastScreenWindowed(self, widget):
        self._broadcastScreen('')


    def stopTransmissions(self, widget):
        self.execOnClients(['stop_receptions'], self.cstore,
            mode=EM_SYSTEM_AND_SESSION)
        if not self.vncserver is None:
            self.vncserver.kill()
            self.vncserver = None


    ## FIXME FIXME: Should we allow for running arbitrary commands in clients?
    def execDialog(self, widget):
        cmd = startExecuteCmdDlg()
        # If Cancel or Close were clicked
        if cmd == '':
            return
        em = EM_SESSION
        if cmd[:5] == 'sudo ':
            em = EM_SYSTEM
            cmd = cmd[4:]
        self.execOnSelectedClients(['execute', cmd], mode=em)


    def sendMessageDialog(self, widget):
        msg = startSendMessageDlg()
        if msg:
            cmd = list(msg)
            cmd.insert(0, 'message')
            self.execOnSelectedClients(cmd)


    ## FIXME / FIXUS: Should we allow it?
    def openTerminal(self, em):
        clients = self.getSelectedClients()
        
        # If there is no client selected, send the command to all
        if len(clients) == 0:
            clients = self.cstore

        for client in clients:
            inst = client[C_INSTANCE]
            if inst.type == 'offline':
                continue

            port = self.findUnusedPort()

            subprocess.Popen(['xterm', '-e', 'socat',
                'tcp-listen:%d,keepalive=1' % port, 'stdio,raw,echo=0'])
            self.execOnClients(['remote_term', port], [client], mode=em)


    def openUserTerminal(self, widget):
        self.openTerminal(EM_SESSION)


    def openRootTerminal(self, widget):
        self.openTerminal(EM_SYSTEM)


    def remoteRootTerminal(self, widget):
        self.execOnSelectedClients(['root_term'], mode=EM_SYSTEM)
    ## END_FIXUS


    def lockScreen(self, widget):
        """
        Lock screen for all the selected clients, displaying a message
        """
        msg = _("The screen is locked by a system administrator.")
        self.execOnSelectedClients(['lock_screen', 0, msg])


    def unlockScreen(self, widget):
        """
        Unlock screen for all clients selected
        """
        self.execOnSelectedClients(['unlock_screen'], mode=EM_SESSION_AND_SYSTEM)


    def soundOff(self, widget):
        """
        Disable sound usage for clients selected
        """
        self.execOnSelectedClients(['mute_sound', 0], mode=EM_SYSTEM_OR_SESSION)


    def soundOn(self, widget):
        """
        Enable sound usage for clients selected
        """
        self.execOnSelectedClients(['unmute_sound'], mode=EM_SYSTEM_AND_SESSION)


    def on_remove_from_group_clicked(self, widget):
        clients = self.getSelectedClients()
        group = self.getSelectedGroup()[1]
        
        if self.warnDlgPopup(_('Are you sure you want to remove the selected client(s) from group "%s"?') %group.name):
            for client in clients:
                group.remove_client(client[C_INSTANCE])
            self.fillIconView(self.getSelectedGroup()[1], True)


    def set_move_group_sensitivity(self):
        selected = self.getSelectedGroup()
        selected_path = self.gstore.get_path(selected[0])[0]
        blocker = not selected[1] is self.default_group
        self.get('move_group_up').set_sensitive(blocker and selected_path > 1)
        self.get('move_group_down').set_sensitive(blocker and selected_path < len(self.gstore)-1)


    def on_move_group_down_clicked(self, widget):
        selected_group_iter = self.getSelectedGroup()[0]
        self.gstore.swap(selected_group_iter, self.gstore.iter_next(selected_group_iter))
        self.set_move_group_sensitivity()


    def on_move_group_up_clicked(self, widget):
        selected_group_iter = self.getSelectedGroup()[0]
        previous_iter = self.gstore.get_iter(self.gstore.get_path(selected_group_iter)[0]-1)
        self.gstore.swap(selected_group_iter, previous_iter)
        self.set_move_group_sensitivity()


    def on_remove_group_clicked(self, widget):
        group_iter = self.getSelectedGroup()[0]
        group = self.gstore[group_iter][G_INSTANCE]
        
        if self.warnDlgPopup(_('Are you sure you want to remove group "%s"?') % group.name):
            self.gstore.remove(group_iter)


    def on_add_group_clicked(self, widget):
        new_group = structs.Group()
        iter = self.gstore.append([new_group.name, new_group, True])
        # Edit the name of the newly created group
        self.gtree.set_cursor(self.gstore.get_path(iter), self.get('group_name_column'), True)


    def on_group_renamed(self, widget, path, new_name):
        self.gstore[path][G_LABEL] = new_name
        self.gstore[path][G_INSTANCE].name = new_name


    #FIXME: Remove the second parameter, find a better way
    def on_tb_client_properties_clicked(self, widget=None):
        dlg = ClientInformation(self.getSelectedClients(), self.daemon.command)
        if self.isDefaultGroupSelected():
            dlg.edit_button.set_sensitive(False)
        dlg.run()
        self.setLabel(self.getSelectedClients()[0])


    def on_mi_remote_assistance_activate(self, widget=None):
        path = '/usr/share/epoptes-client'
        subprocess.Popen('%s/remote-assistance' %path, shell=True, cwd=path)


    def on_mi_about_activate(self, widget=None):
        About().run()


    def on_cViewHU_toggled(self, mitem):
        self.set_cView(1, 0)
        config.settings.set('GUI', 'label', 'miClientsViewHostUser')


    def on_cViewUH_toggled(self, mitem):
        self.set_cView(0, 1)
        config.settings.set('GUI', 'label', 'miClientsViewUserHost')


    def on_cViewH_toggled(self, mitem):
        self.set_cView(-1, 0)
        config.settings.set('GUI', 'label', 'miClientsViewHost')


    def on_cViewU_toggled(self, mitem):
        self.set_cView(0, -1)
        config.settings.set('GUI', 'label', 'miClientsViewUser')


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
        d = self.daemon.command(handle, u'info')
        d.addCallback(lambda r: self.addClient(handle, r))
        d.addErrback(lambda err: self.printErrors("when connecting client %s: %s" %(handle, err)))


    def amp_clientDisconnected(self, handle):
        print "Disconnect from", handle
        
        def determine_offline(client):
            if client.hsystem == '' and client.users == {}:
                client.set_offline()
        client = None
        for client in structs.clients:
            if client.hsystem == handle:
                if self.getSelectedGroup()[1].has_client(client) or self.isDefaultGroupSelected():
                    shutdownNotify(client.get_name())
                client.hsystem = ''
                determine_offline(client)
                break
            
            elif handle in client.users:
                if self.getSelectedGroup()[1].has_client(client) or self.isDefaultGroupSelected():
                    logoutNotify(client.users[handle]['uname'], client.get_name())
                del client.users[handle]
                determine_offline(client)
                break
            else:
                client = None

        if not client is None:
            for row in self.cstore:
                if row[C_INSTANCE] is client: 
                    self.fillIconView(self.getSelectedGroup()[1], True)
                    break


    def amp_gotClients(self, handles):
        print "Got clients:", ', '.join(handles) or 'None'
        for handle in handles:
            d = self.daemon.command(handle, u'info')
            d.addCallback(lambda r, h=handle: self.addClient(h, r, True))
            d.addErrback(lambda err: self.printErrors("when enumerating client %s: %s" %(handle, err)))


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
        self.set_move_group_sensitivity()


    def addToIconView(self, client):
        """Properly add a Client class instance to the clients iconview."""
        # If there are one or more users on client, add a new iconview entry
        # for each one of them.
        
        label = 'uname'
        if self.showRealNames:
                label = 'rname'
        if client.users:
            for hsession, user in client.users.iteritems():
                self.cstore.append([self.calculateLabel(client, user[label]), self.imagetypes[client.type], client, hsession])
                self.askScreenshot(hsession, True)
        else:
            self.cstore.append([self.calculateLabel(client), self.imagetypes[client.type], client, ''])


    def fillIconView(self, group, keep_selection=False):
        """Fill the clients iconview from a Group class instance."""
        if keep_selection:
            selection = [row[C_INSTANCE] for row in self.getSelectedClients()]
        self.cstore.clear()
        if self.isDefaultGroupSelected():
            clients_list = [client for client in structs.clients if client.type != 'offline']
        else:
            clients_list = group.get_members()
        # Add the new clients to the iconview
        for client in clients_list:
            self.addToIconView(client)
        if keep_selection:
            for row in self.cstore:
                if row[C_INSTANCE] in selection:
                    self.cview.select_path(row.path)
                    selection.remove(row[C_INSTANCE])


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
        print "---\n**addClient's been called for", handle
        try:
            info = {}
            for line in r.strip().split('\n'):
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()
            user, host, ip, mac, type, uid, version, name = \
                info['user'], info['hostname'], info['ip'], info['mac'], \
                info['type'], int(info['uid']), info['version'], info['name']
        except:
            print "Can't extract client information, won't add this client"
            return
        
        # Check if the incoming client is the same with the computer in which
        # epoptes is running, so we don't add it to the list.
        # FIXME FiXME: Both ifs don't work for root clients that run in the same
        # computer as epoptes
        if (mac in self.current_macs) and (uid == self.uid):
            print "* Won't add this client to my lists"
            return False
        
        print '  Continuing inside addClient...'
        
        # Compatibility check
        if [int(x) for x in re.split('[^0-9]*', version)] < COMPATIBILITY_VERSION:
            if not self.shownCompatibilityWarning:
                self.shownCompatibilityWarning = True
                dlg = self.get('warningDialog')
                # Show different messages for LTSP clients and standalones.
                msg = _("A connection attempt was made by a client with version %s, \
which is incompatible with the current epoptes version.\
\n\nYou need to update your clients to the latest epoptes-client version.") % version
                dlg.set_property('text', msg)
                dlg.set_transient_for(self.mainwin)
                dlg.show()
            self.daemon.command(handle, u"exit")
            return False
        sel_group = self.getSelectedGroup()[1]
        client = None
        for inst in structs.clients:
            # Find if the new handle is a known client
            if mac == inst.mac:
                client = inst
                print '* This is an existing client'
                break
        if client is None:
            print '* This client is a new one, creating an instance'
            client = structs.Client(mac=mac)
            
        # Update/fill the client information
        client.type, client.hostname = type, host
        if uid == 0:
            # This is a root epoptes-client
            print '* I am a root client'
            client.hsystem = handle
        else:
            # This is a user epoptes-client
            print '* I am a user client, will add', user, 'in my list'
            client.add_user(user, name, handle)
            if not already and (sel_group.has_client(client) or self.isDefaultGroupSelected()):
                loginNotify(user, host)
        
        if sel_group.has_client(client) or self.isDefaultGroupSelected():
            self.fillIconView(sel_group, True)


    def setLabel(self, row):
        inst = row[C_INSTANCE]
        if row[C_SESSION_HANDLE]:            
            label = 'uname'
            if self.showRealNames:
                label = 'rname'
            user = row[C_INSTANCE].users[row[C_SESSION_HANDLE]][label]
        else:
            user = ''
        row[C_LABEL] = self.calculateLabel(inst, user)


    def calculateLabel(self, client, username=''):
        """Return the iconview label from a hostname/alias
        and a username, according to the user options.
        """
        user_pos, name_pos = self.cView_order
        
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


    def getShowRealNames(self):
        return self.get('')
    
    
    def screenshotTimeout(self, handle):
        print "Screenshot for client %s timed out. Requesting a new one..." % handle
        self.askScreenshot(handle)
        return False


    def askScreenshot(self, handle, firstTime=False):
        # Should always return False to prevent glib from calling us again
        if firstTime:
            if not handle in self.currentScreenshots:
                # Mark that we started asking for screenshots, but didn't yet get one
                self.currentScreenshots[handle] = None
            else:
                # We're already asking the client for screenshots, reuse the existing one
                if not self.currentScreenshots[handle] is None:
                    for i in self.cstore:
                        if handle == i[C_SESSION_HANDLE]:
                            self.cstore[i.path][C_PIXBUF] = self.currentScreenshots[handle]
                            break
                return False
        # TODO: Implement this using gtk.TreeRowReferences instead
        # of searching the whole model (Need to modify execOnClients)
        for client in self.cstore:
            if handle == client[C_SESSION_HANDLE]:
                timeoutID = gobject.timeout_add(10000, lambda h=handle: self.screenshotTimeout(h))
                self.execOnClients(['screenshot', self.scrWidth, self.scrHeight], handles=[handle], 
                                   reply=self.gotScreenshot, params=[timeoutID])
                return False
        # That handle is no longer in the cstore, remove it
        try: del self.currentScreenshots[handle]
        except: pass
        return False


    def gotScreenshot(self, handle, reply, timeoutID):
        # Cancel the timeout event. If it already happened, exit.
        if not gobject.source_remove(timeoutID):
            return
        for i in self.cstore:
            if handle == i[C_SESSION_HANDLE]:
                # We want to ask for thumbnails every 5 sec after the last one.
                # So if the client is too stressed and needs 7 secs to
                # send a thumbnail, we'll ask for one every 12 secs.
                gobject.timeout_add(5000, self.askScreenshot, handle)
#                print "I got a screenshot from %s." % handle
                if not reply:
                    return
                try:
                    rowstride, size, pixels = reply.split('\n', 2)
                except:
                    return
                rowstride = int(rowstride)
                width, height = size.split('x')
                pxb = gtk.gdk.pixbuf_new_from_data(pixels,
                    gtk.gdk.COLORSPACE_RGB, False, 8, int(width), int(height),
                    rowstride)
                self.currentScreenshots[handle] = pxb
                self.cstore[i.path][C_PIXBUF] = pxb
                return
        # That handle is no longer in the cstore, remove it
        try: del self.currentScreenshots[handle]
        except: pass


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
        self.openLink("http://www.epoptes.org")


    def openBugsLink(self, widget):
        self.openLink("https://bugs.launchpad.net/epoptes")


    def openQuestionsLink(self, widget):
        self.openLink("https://answers.launchpad.net/epoptes")


    def openTranslationsLink(self, widget):
        self.openLink("http://www.epoptes.org/translations")


    def openIRCLink(self, widget):
        user = os.getenv("USER")
        if user is None:
            user = "epoptes_user." # The dot is converted to a random digit
        self.openLink("http://webchat.freenode.net/?nick=" + user + 
            "&channels=ltsp&prompt=1")
    
    
    def iconsSizeScale_button_event(self, widget, event):
        """A hack to make the left click work like middle click
        in the scale (for jump-to functionality). Right click resets
        the thumbnail size.
        """
        if event.button == 1:
            event.button = 2
        elif event.button == 3:
            self.iconsSizeScaleChanged(None, 120) # Reset the thumbnail size
        return False
    
    
    def reload_imagetypes(self):
        """Improve the quality of previously resized svg icons,
        by reloading them.
        """
        old_pixbufs = self.imagetypes.values()
        loadSVG = lambda path: gtk.gdk.pixbuf_new_from_file_at_size(path, 
                                                  self.scrWidth, self.scrHeight)
        self.imagetypes = {
            'offline' : loadSVG('images/offline.svg'),
            'thin' : loadSVG('images/thin.svg'),
            'fat' : loadSVG('images/fat.svg'),
            'standalone' : loadSVG('images/standalone.svg')
        }
        
        rows = [row for row in self.cstore if row[C_PIXBUF] in old_pixbufs]
        for row in rows:
            row[C_PIXBUF] = self.imagetypes[row[C_INSTANCE].type]
    
    
    def on_iconsSizeScale_button_release_event(self, widget=None, event=None):
        # Here we want to resize the SVG icons from imagetypes at a better
        # quality than this of the quick pixbuf scale, since we assume that
        # the user has decided the desired zoom level.
        self.reload_imagetypes()
    
    
    def iconsSizeScaleChanged(self, widget=None, width=None):
        adj = self.get('iconsSizeAdjustment')
        if width:
            adj.set_value(width)
        else:
            width = adj.get_value()
        self.scrWidth = int(width)
        self.scrHeight = int(3 * self.scrWidth / 4) # Κeep the 4:3 aspect ratio
        
        # Fast scale all the thumbnails to make the change quickly visible
        old_pixbufs = self.imagetypes.values()
        for row in self.cstore:
            if row[C_PIXBUF] in old_pixbufs:
                ctype = row[C_INSTANCE].type
                cur_w = self.imagetypes[ctype].get_width()
                cur_h = self.imagetypes[ctype].get_height()
                if not (cur_w == self.scrWidth and cur_h == self.scrHeight):
                    new_thumb = row[C_PIXBUF].scale_simple(self.scrWidth, self.scrHeight, gtk.gdk.INTERP_NEAREST)
                    self.imagetypes[ctype] = new_thumb
                row[C_PIXBUF] = self.imagetypes[ctype]
            else:
                new_thumb = row[C_PIXBUF].scale_simple(self.scrWidth, self.scrHeight, gtk.gdk.INTERP_NEAREST)
                row[C_PIXBUF] = new_thumb
        
        # Hack to remove the extra padding that remains after a 'zoom out'
        self.cview.set_resize_mode(gtk.RESIZE_IMMEDIATE)
        self.cview.get_cells()[1].set_fixed_size(-1, -1)
        self.cview.check_resize()
    
    
    def scrIncreaseSize(self, widget):
        # Increase the size of screenshots by 2 pixels in width
        adj = self.get('iconsSizeAdjustment')
        adj.set_value(adj.get_value() + 15)
        self.reload_imagetypes()


    def scrDecreaseSize(self, widget):
        # Decrease the size of screenshots by 2 pixels in width
        adj = self.get('iconsSizeAdjustment')
        adj.set_value(adj.get_value() - 15)
        self.reload_imagetypes()
    
    
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


    def on_clients_selection_changed(self, widget=None):
        selected = self.getSelectedClients()
        sensitive = False
        if len(selected) == 1:
            sensitive = True
        self.get('miClientProperties').set_sensitive(sensitive)
        self.get('tb_client_properties').set_sensitive(sensitive)
        
        if len(selected) > 0 and not self.isDefaultGroupSelected():
            self.get('miRemoveFromGroup').set_sensitive(True)
        else:
            self.get('miRemoveFromGroup').set_sensitive(False)
        
        if len(selected) > 1:
            self.get('statusbar_label').set_text(_('%d clients selected' % len(selected)))
        else:
            self.get('statusbar_label').set_text('')


    def execOnClients(self, command, clients=[], reply=None,
            mode=EM_SESSION_OR_SYSTEM, handles=[], warning='', params=None):
        '''reply should be a method in which the result will be sent'''
        if params is None:
            params = []
        if len(self.cstore) == 0:
            # print 'No clients'
            return False
        
        if isinstance(command, list) and len(command) > 0:
            command = '%s %s' %(command[0], ' '.join([pipes.quote(str(x)) for x in command[1:]]))
                    
        if (clients != [] or handles != []) and warning != '':
            if self.warnDlgPopup(warning) == False:
                return
        if clients == [] and handles != []:
            for handle in handles:
                cmd = self.daemon.command(handle, unicode(command))
                if reply:
                    cmd.addCallback(lambda re, h=handle, p=params: reply(h, re, *p))
                    cmd.addErrback(lambda err: self.printErrors("when executing command %s on client %s: %s" %(command,handle, err)))

        for client in clients:
            sent = False
            for em in mode:
                if em == EM_SESSION_ONLY:
                    handle = client[C_SESSION_HANDLE]
                elif em == EM_SYSTEM_ONLY:
                    handle = client[C_INSTANCE].hsystem
                else: # em == EM_EXIT_IF_SENT
                    if sent:
                        break
                    else:
                        continue
                if handle == '':
                    continue
                sent = True
                cmd = self.daemon.command(handle, unicode(command))
                if reply:
                    cmd.addCallback(lambda re, h=handle, p=params: reply(h, re, *p))
                    cmd.addErrback(lambda err: self.printErrors("when executing command %s on client %s: %s" %(command,handle, err)))


    def execOnSelectedClients(self, command, reply=None,
            mode=EM_SESSION_OR_SYSTEM, warn=''):
        clients = self.getSelectedClients()
        if len(clients) == 0: # No client selected, send the command to all
            clients = self.cstore
        else: # Show the warning only when no clients are selected
            warn = ''
        self.execOnClients(command, clients, reply, mode, warning=warn)


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


    def printErrors(self, error):
        print '  **Twisted error:', error
        return
