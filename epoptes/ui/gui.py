#!/usr/bin/env python3
# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Epoptes GUI class.
"""
from distutils.version import LooseVersion
import getpass
import locale
import os
import pipes
import socket

from epoptes.ui.reactor import reactor
from epoptes.common.constants import *
from epoptes.common import config
from epoptes.core import structs
from epoptes.core import wol
from epoptes.core.lib_users import *
from epoptes.ui.about import About
from epoptes.ui.benchmark import Benchmark
from epoptes.ui.client_information import ClientInformation
from epoptes.ui.common import gettext as _
from epoptes.ui.exec_command import ExecCommand
from epoptes.ui.notifications import NotifyQueue
from epoptes.ui.send_message import SendMessage

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


class EpoptesGui(object):

    def __init__(self):
        self.about = None
        self.client_information = None
        self.exec_command = None
        self.benchmark = None
        self.notify_queue = NotifyQueue(
            'Epoptes',
            '/usr/share/icons/hicolor/scalable/apps/epoptes.svg')
        self.send_message = None
        self.shownCompatibilityWarning = False
        self.vncserver = None
        self.vncviewer = None
        self.scrWidth = 100
        self.scrHeight = 75
        self.showRealNames = False
        self.currentScreenshots = dict()
        self.current_macs = subprocess.Popen([
            'sh', '-c',
            """ip -oneline -family inet link show | """
            """sed -n '/.*ether[[:space:]]*\\([[:xdigit:]:]*\).*/"""
            """{s//\\1/;y/abcdef-/ABCDEF:/;p;}';"""
            """echo $LTSP_CLIENT_MAC"""],
            stdout=subprocess.PIPE).communicate()[0].split()
        self.uid = os.getuid()
        if 'thumbnails_width' in config.user:
            self.scrWidth = config.user['thumbnails_width']
        self.offline = GdkPixbuf.Pixbuf.new_from_file('images/offline.svg')
        self.thin = GdkPixbuf.Pixbuf.new_from_file('images/thin.svg')
        self.fat = GdkPixbuf.Pixbuf.new_from_file('images/fat.svg')
        self.standalone = GdkPixbuf.Pixbuf.new_from_file(
            'images/standalone.svg')
        self.imagetypes = {
            'thin': self.thin, 'fat': self.fat,
            'standalone': self.standalone, 'offline': self.offline}

        self.wTree = Gtk.Builder()
        self.wTree.add_from_file('epoptes.ui')

        self.get = lambda obj: self.wTree.get_object(obj)

        # Connect glade handlers with the callback functions
        self.wTree.connect_signals(self)

        # Hide the remote assistance menuitem if epoptes-client is not installed
        if not os.path.isfile('/usr/share/epoptes-client/remote_assistance.py'):
            self.get('mi_remote_assistance').set_property('visible', False)
            self.get('remote_assistance_separator').set_property('visible',
                                                                 False)

        self.groups_menu = self.get('mAddToGroup')
        self.add_to_group_menu = self.get('miAddToGroup')

        self.gstore = Gtk.ListStore(str, object, bool)

        self.gtree = self.get("groups_tree")
        self.gtree.set_model(self.gstore)
        self.gtree.get_selection().connect("changed",
                                           self.on_group_selection_changed)

        self.mainwin = self.get('mainwindow')

        self.cstore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, object, str)
        self.cview = self.get('clientsview')
        self.cView_order = (1, 0)
        self.set_cView(*self.cView_order)

        self.cview.set_model(self.cstore)
        self.cview.set_pixbuf_column(C_PIXBUF)
        self.cview.set_text_column(C_LABEL)

        self.cstore.set_sort_column_id(C_LABEL, Gtk.SortType.ASCENDING)
        self.on_clients_selection_changed()

        self.cview.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new("add", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.COPY)
        self.gtree.enable_model_drag_dest(
            [("add", Gtk.TargetFlags.SAME_APP, 0)], Gdk.DragAction.COPY)

        self.default_group = structs.Group('<b>'+_('Detected clients')+'</b>')
        default_iter = self.gstore.append(
            [self.default_group.name, self.default_group, False])
        self.default_group.ref = Gtk.TreeRowReference(
            self.gstore, self.gstore.get_path(default_iter))
        self.gtree.get_selection().select_path(
            self.default_group.ref.get_path())

        self.get('iconsSizeAdjustment').set_value(self.scrWidth)
        self.reload_imagetypes()

        saved_clients, groups = config.read_groups(
            os.path.expanduser('~/.config/epoptes/groups.json'))
        if len(groups) > 0:
            self.add_to_group_menu.set_sensitive(True)
        for grp in groups:
            self.gstore.append([grp.name, grp, True])
            mitem = Gtk.MenuItem(label=grp.name)
            mitem.show()
            mitem.connect('activate', self.on_add_to_group_clicked, grp)
            self.groups_menu.append(mitem)

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
            self.get('mcShowRealNames').set_active(
                config.settings.getboolean('GUI', 'showRealNames'))
        self.mainwin.set_sensitive(False)


    #################################################################
    #                       Callback functions                      #
    #################################################################
    def on_gtree_drag_motion(self, widget, context, x, y, etime):
        drag_info = widget.get_dest_row_at_pos(x, y)
        # Don't allow dropping in the empty space of the treeview,
        # or inside the 'Detected' group, or inside the currently selected group
        selected_path = self.gstore.get_path(self.getSelectedGroup()[0])
        if (not drag_info or drag_info[0] == self.default_group.ref.get_path()
                or drag_info[0] == selected_path):
            widget.set_drag_dest_row(None, Gtk.TreeViewDropPosition.AFTER)
        else:
            path, pos = drag_info
            # Don't allow dropping between the groups treeview rows
            if pos == Gtk.TreeViewDropPosition.BEFORE:
                widget.set_drag_dest_row(
                    path, Gtk.TreeViewDropPosition.INTO_OR_BEFORE)
            elif pos == Gtk.TreeViewDropPosition.AFTER:
                widget.set_drag_dest_row(
                    path, Gtk.TreeViewDropPosition.INTO_OR_AFTER)

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

    def save_settings(self):
        sel_group = self.gstore.get_path(self.getSelectedGroup()[0])[0]
        self.gstore.remove(self.gstore.get_iter(
            self.default_group.ref.get_path()))
        config.save_groups(os.path.expanduser('~/.config/epoptes/groups.json'),
                           self.gstore)
        settings = config.settings
        if not settings.has_section('GUI'):
            settings.add_section('GUI')

        settings.set('GUI', 'selected_group', str(sel_group))
        settings.set('GUI', 'showRealNames', str(self.showRealNames))
        settings.set('GUI', 'thumbnails_width', str(self.scrWidth))
        try:
            f = open(os.path.expanduser('~/.config/epoptes/settings'), 'w')
            settings.write(f)
            f.close()
        except:
            pass

    def on_mainwin_destroy(self, widget):
        """
        Quit clicked

        Close main window
        """
        self.save_settings()
        if self.vncserver is not None:
            self.vncserver.kill()
        if self.vncviewer is not None:
            self.vncviewer.kill()
        reactor.stop()

    def on_miBenchmark_activate(self, _widget):
        if not self.benchmark:
            self.benchmark = Benchmark(self.mainwin, self.daemon.command)
        self.benchmark.run(self.getSelectedClients() or self.cstore)

    def toggleRealNames(self, widget=None):
        """Show/hide the real names of the users instead of the usernames"""
        self.showRealNames = widget.get_active()
        for row in self.cstore:
            self.setLabel(row)

    def wake_on_lan(self, widget):
        """Boot the selected computers with WOL"""
        clients = self.getSelectedClients()
        if len(clients) == 0:  # No client selected, send the command to all
            clients = self.cstore
        for client in clients:
            # Make sure that only offline computers will be sent to wol
            client = client[C_INSTANCE]
            if client.is_offline():
                wol.wake_on_lan(client.mac)

    def poweroff(self, widget):
        """Shut down the selected clients."""
        self.execOnSelectedClients(
            ["shutdown"],
            warn=_('Are you sure you want to shutdown all the computers?'))

    def reboot(self, widget):
        """Reboot the selected clients."""
        self.execOnSelectedClients(
            ["reboot"],
            warn=_('Are you sure you want to reboot all the computers?'))

    def logout(self, widget):
        """Log off the users of the selected clients."""
        self.execOnSelectedClients(
            ['logout'], mode=EM_SESSION,
            warn=_('Are you sure you want to log off all the users?'))

    def reverseConnection(self, widget, path, view_column, cmd, *args):
        # Open vncviewer in listen mode
        if self.vncviewer is None or self.vncviewer.poll() is not None:
            self.vncviewerport = self.findUnusedPort()
            # If the user installed ssvnc, prefer it over xvnc4viewer
            if os.path.isfile('/usr/bin/ssvncviewer'):
                self.vncviewer = subprocess.Popen(
                    ['ssvncviewer', '-multilisten',
                     str(self.vncviewerport-5500)])
            elif os.path.isfile('/usr/bin/xtigervncviewer'):
                self.vncviewer = subprocess.Popen(
                    ['xtigervncviewer', '-listen', str(self.vncviewerport)])
            elif os.path.isfile('/usr/bin/xvnc4viewer'):
                self.vncviewer = subprocess.Popen(
                    ['xvnc4viewer', '-listen', str(self.vncviewerport)])
            # Support tigervnc on rpm distributions (LP: #1501747)
            elif os.path.isfile('/usr/share/locale/de/LC_MESSAGES/tigervnc.mo'):
                self.vncviewer = subprocess.Popen(
                    ['vncviewer', '-listen', str(self.vncviewerport)])
            # The rest of the viewers, like tightvnc
            else:
                self.vncviewer = subprocess.Popen(
                    ['vncviewer', '-listen', str(self.vncviewerport-5500)])

        # And, tell the clients to connect to the server
        self.execOnSelectedClients([cmd, self.vncviewerport] + list(args))

    def assistUser(self, widget, path=None, view_column=None):
        if config.settings.has_option('GUI', 'grabkbdptr'):
            grab = config.settings.getboolean('GUI', 'grabkbdptr')
        if grab:
            self.reverseConnection(
                widget, path, view_column, 'get_assisted', 'True')
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
            pwd=''.join(random.sample(string.ascii_letters + string.digits, 8))
            subprocess.call(['x11vnc', '-storepasswd', pwd, pwdfile])
            f=open(pwdfile, 'rb')
            pwd=f.read()
            f.close()
            self.pwd = ''.join('\\%o' % c for c in pwd)
            self.vncserverport = self.findUnusedPort()
            self.vncserver = subprocess.Popen(
                ['x11vnc', '-noshm', '-nopw', '-quiet', '-viewonly', '-shared',
                 '-forever', '-nolookup', '-24to32', '-threads', '-rfbport',
                 str(self.vncserverport), '-rfbauth', pwdfile])
        # Running `xdg-screensaver reset` as root doesn't reset the D.E.
        # screensaver, so send the reset command to both epoptes processes
        self.execOnSelectedClients(
            ['reset_screensaver'], mode=EM_SYSTEM_AND_SESSION)
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
        if not self.exec_command:
            self.exec_command = ExecCommand(self.mainwin)
        cmd = self.exec_command.run()
        # If Cancel or Close were clicked
        if cmd == '':
            return
        if cmd.startswith("sudo "):
            em = EM_SYSTEM
            cmd = cmd[5:]
        else:
            em = EM_SESSION
        self.execOnSelectedClients(['execute', cmd], mode=em)

    def sendMessageDialog(self, widget):
        if not self.send_message:
            self.send_message = SendMessage(self.mainwin)
        params = self.send_message.run()
        if params:
            self.execOnSelectedClients(['message'] + list(params))

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

            user = '--'
            if em == EM_SESSION and client[C_SESSION_HANDLE]:
                user = inst.users[client[C_SESSION_HANDLE]]['uname']
            elif em == EM_SYSTEM:
                user = 'root'
            title = '%s@%s' % (user, inst.get_name())
            subprocess.Popen(['xterm', '-T', title, '-e', 'socat',
                              'tcp-listen:%d,keepalive=1' % port,
                              'stdio,raw,echo=0'])
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
        self.execOnSelectedClients(
            ['unlock_screen'], mode=EM_SESSION_AND_SYSTEM)

    def soundOff(self, widget):
        """
        Disable sound usage for clients selected
        """
        self.execOnSelectedClients(
            ['mute_sound', 0], mode=EM_SYSTEM_OR_SESSION)

    def soundOn(self, widget):
        """
        Enable sound usage for clients selected
        """
        self.execOnSelectedClients(
            ['unmute_sound'], mode=EM_SYSTEM_AND_SESSION)

    def on_add_to_group_clicked(self, widget, group):
        clients = self.getSelectedClients()
        for client in clients:
            if not group.has_client(client[C_INSTANCE]):
                group.add_client(client[C_INSTANCE])

    def on_remove_from_group_clicked(self, widget):
        clients = self.getSelectedClients()
        group = self.getSelectedGroup()[1]

        if self.warnDlgPopup(
                _('Are you sure you want to remove '
                  'the selected client(s) from group "%s"?') %group.name):
            for client in clients:
                group.remove_client(client[C_INSTANCE])
            self.fillIconView(self.getSelectedGroup()[1], True)

    def set_move_group_sensitivity(self):
        selected = self.getSelectedGroup()
        selected_path = self.gstore.get_path(selected[0])[0]
        blocker = not selected[1] is self.default_group
        self.get('move_group_up').set_sensitive(blocker and selected_path > 1)
        self.get('move_group_down').set_sensitive(
            blocker and selected_path < len(self.gstore)-1)

    def on_move_group_down_clicked(self, widget):
        selected_group_iter = self.getSelectedGroup()[0]
        path = self.gstore.get_path(selected_group_iter)[0]
        self.gstore.swap(selected_group_iter,
                         self.gstore.iter_next(selected_group_iter))
        self.set_move_group_sensitivity()
        mitem = self.groups_menu.get_children()[path-1]
        self.groups_menu.reorder_child(mitem, path)

    def on_move_group_up_clicked(self, widget):
        selected_group_iter = self.getSelectedGroup()[0]
        path = self.gstore.get_path(selected_group_iter)[0]
        previous_iter = self.gstore.get_iter(path-1)
        self.gstore.swap(selected_group_iter, previous_iter)
        self.set_move_group_sensitivity()
        mitem = self.groups_menu.get_children()[path-1]
        self.groups_menu.reorder_child(mitem, path-2)

    def on_remove_group_clicked(self, widget):
        group_iter = self.getSelectedGroup()[0]
        group = self.gstore[group_iter][G_INSTANCE]

        if self.warnDlgPopup(
                _('Are you sure you want to remove group "%s"?') % group.name):
            path = self.gstore.get_path(group_iter)[0]
            self.gstore.remove(group_iter)
            menuitem = self.groups_menu.get_children()[path-1]
            self.groups_menu.remove(menuitem)

    def on_add_group_clicked(self, widget):
        new_group = structs.Group()
        iter = self.gstore.append([new_group.name, new_group, True])
        # Edit the name of the newly created group
        self.gtree.set_cursor(self.gstore.get_path(iter),
                              self.get('group_name_column'), True)
        self.appendToGroupsMenu(new_group)

    def on_group_renamed(self, widget, path, new_name):
        self.gstore[path][G_LABEL] = new_name
        self.gstore[path][G_INSTANCE].name = new_name
        self.groups_menu.get_children()[int(path)-1].set_label(new_name)

    def on_tb_client_properties_clicked(self, _widget):
        if not self.client_information:
            self.client_information = ClientInformation(self.mainwin)
        self.client_information.btn_edit_alias.set_sensitive(
            not self.isDefaultGroupSelected())
        self.client_information.run(
            self.getSelectedClients()[0], self.daemon.command)
        self.setLabel(self.getSelectedClients()[0])

    def on_mi_remote_assistance_activate(self, widget=None):
        path = '/usr/share/epoptes-client'
        subprocess.Popen('%s/remote_assistance.py' % path, shell=True, cwd=path)

    def on_mi_about_activate(self, widget=None):
        if not self.about:
            self.about = About(self.mainwin)
        self.about.run()

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

    # TODO: this is callback from uiconnection.py
    def connected(self, daemon):
        self.mainwin.set_sensitive(True)
        self.daemon = daemon
        daemon.enumerate_clients().addCallback(lambda h: self.amp_gotClients(h))
        self.fillIconView(self.getSelectedGroup()[1])

    def disconnected(self, daemon):
        self.mainwin.set_sensitive(False)
        # If the reactor is not running at this point it means that we were
        # closed normally.
        if not reactor.running:
            return
        self.save_settings()
        msg = _("Lost connection with the epoptes service.")
        msg += "\n\n" + \
               _("Make sure the service is running and then restart epoptes.")
        dlg = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK, message_format=msg)
        dlg.set_title(_('Service connection error'))
        dlg.run()
        dlg.destroy()
        reactor.stop()

    # AMP callbacks
    def amp_client_connected(self, handle):
        print("New connection from", handle)
        d = self.daemon.command(handle, 'info')
        d.addCallback(lambda r: self.addClient(handle, r.decode()))
        d.addErrback(lambda err: self.printErrors(
            "when connecting client %s: %s" % (handle, err)))

    def amp_client_disconnected(self, handle):
        print("Disconnect from", handle)

        def determine_offline(client):
            if client.hsystem == '' and client.users == {}:
                client.set_offline()
        client = None
        for client in structs.clients:
            if client.hsystem == handle:
                if self.getSelectedGroup()[1].has_client(client) \
                        or self.isDefaultGroupSelected():
                    self.notify_queue.enqueue(
                        _("Shut down:"), client.get_name())
                client.hsystem = ''
                determine_offline(client)
                break

            elif handle in client.users:
                if self.getSelectedGroup()[1].has_client(client) \
                        or self.isDefaultGroupSelected():
                    self.notify_queue.enqueue(
                        _("Disconnected:"),
                        _("%(user)s from %(host)s") %
                        {"user": client.users[handle]['uname'],
                         "host": client.get_name()})
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
        print( "Got clients:", ', '.join(handles) or 'None')
        for handle in handles:
            d = self.daemon.command(handle, 'info')
            d.addCallback(
                lambda r, h=handle: self.addClient(h, r.decode(), True))
            d.addErrback(lambda err: self.printErrors(
                "when enumerating client %s: %s" %(handle, err)))

    def on_button_close_clicked(self, widget):
        self.get('warningDialog').hide()

    def on_group_selection_changed(self, treeselection):
        self.cstore.clear()
        selected = self.getSelectedGroup()

        if selected is not None:
            self.fillIconView(selected[1])
            path = self.gstore.get_path(selected[0])[0]
            self.groups_menu.foreach(lambda w : w.set_sensitive(True))
            menuitems = self.groups_menu.get_children()
            if path != 0 and path-1 < len(menuitems):
                menuitems[path-1].set_sensitive(False)
        else:
            if not self.default_group.ref.valid():
                return
            self.gtree.get_selection().select_path(
                self.default_group.ref.get_path())
        self.get('remove_group').set_sensitive(
            not self.isDefaultGroupSelected())
        self.set_move_group_sensitivity()

    def addToIconView(self, client):
        """Properly add a Client class instance to the clients iconview."""
        # If there are one or more users on client, add a new iconview entry
        # for each one of them.

        label = 'uname'
        if self.showRealNames:
                label = 'rname'
        if client.users:
            for hsession, user in client.users.items():
                self.cstore.append(
                    [self.calculateLabel(client, user[label]),
                     self.imagetypes[client.type], client, hsession])
                self.askScreenshot(hsession, True)
        else:
            self.cstore.append(
                [self.calculateLabel(client),
                 self.imagetypes[client.type], client, ''])

    def fillIconView(self, group, keep_selection=False):
        """Fill the clients iconview from a Group class instance."""
        if keep_selection:
            selection = [row[C_INSTANCE] for row in self.getSelectedClients()]
        self.cstore.clear()
        if self.isDefaultGroupSelected():
            clients_list = [client for client in structs.clients
                            if client.type != 'offline']
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
        if self.getSelectedGroup():
            return self.getSelectedGroup()[1] is self.default_group
        return True

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
        print("addClient's been called for", handle)
        try:
            info = {}
            for line in r.strip().split('\n'):
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()
            user, host, ip, mac, type, uid, version, name = \
                info['user'], info['hostname'], info['ip'], info['mac'], \
                info['type'], int(info['uid']), info['version'], info['name']
        except:
            print("  Can't extract client information, won't add this client")
            return

        # Check if the incoming client is the same with the computer in which
        # epoptes is running, so we don't add it to the list.
        if (mac in self.current_macs) and ((uid == self.uid) or (uid == 0)):
            print("  Won't add this client to my lists")
            return False

        # Compatibility check
        if LooseVersion(version) < LooseVersion(COMPATIBILITY_VERSION):
            if not self.shownCompatibilityWarning:
                self.shownCompatibilityWarning = True
                dlg = self.get('warningDialog')
                # Show different messages for LTSP clients and standalones.
                msg = _("""A connection attempt was made by a client with"""
                        """ version %s, which is incompatible with the"""
                        """ current epoptes version.\n\nYou need to update"""
                        """ your clients to the latest epoptes-client"""
                        """ version.""") % version
                dlg.set_property('text', msg)
                dlg.set_transient_for(self.mainwin)
                dlg.show()
            self.daemon.command(handle, "exit")
            return False
        sel_group = self.getSelectedGroup()[1]
        client = None
        for inst in structs.clients:
            # Find if the new handle is a known client
            if mac == inst.mac:
                client = inst
                print('  Old client: ', end='')
                break
        if client is None:
            print('  New client: ', end='')
            client = structs.Client(mac=mac)
        print('hostname=%s, type=%s, uid=%s, user=%s' % (host, type, uid, user))

        # Update/fill the client information
        client.type, client.hostname = type, host
        if uid == 0:
            # This is a root epoptes-client
            client.hsystem = handle
        else:
            # This is a user epoptes-client
            client.add_user(user, name, handle)
            if not already and (sel_group.has_client(client)
                                or self.isDefaultGroupSelected()):
                self.notify_queue.enqueue(
                    _("Connected:"),
                    _("%(user)s on %(host)s") % {"user": user, "host": host})

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

    def askScreenshot(self, handle, firstTime=False):
        # Should always return False to prevent glib from calling us again
        if firstTime:
            if not handle in self.currentScreenshots:
                # We started asking for thumbshots, but didn't yet get one
                self.currentScreenshots[handle] = None
            else:
                # Reuse the existing thumbshot
                if not self.currentScreenshots[handle] is None:
                    for i in self.cstore:
                        if handle == i[C_SESSION_HANDLE]:
                            self.cstore[i.path][C_PIXBUF] = \
                                self.currentScreenshots[handle]
                            break
                return False
        # TODO: Implement this using Gtk.TreeRowReferences instead
        # of searching the whole model (Need to modify execOnClients)
        for client in self.cstore:
            if handle == client[C_SESSION_HANDLE]:
                # TODO: rename "thumbnail" and "screenshot" to "thumbshot"
                self.execOnClients(
                    ['thumbshot', self.scrWidth, self.scrHeight],
                    handles=[handle], reply=self.gotScreenshot)
                return False
        # That handle is no longer in the cstore, remove it
        try:
            del self.currentScreenshots[handle]
        except:
            pass
        return False

    def gotScreenshot(self, handle, reply):
        for i in self.cstore:
            if handle == i[C_SESSION_HANDLE]:
                # We want to ask for thumbshots every 5 sec after the last one.
                # So if the client is too stressed and needs 7 secs to
                # send a thumbshot, we'll ask for one every 12 secs.
                GLib.timeout_add(5000, self.askScreenshot, handle)
                # print("I got a thumbshot from %s." % handle)
                if not reply:
                    return
                try:
                    rowstride, size, pixels = reply.split(b'\n', 2)
                except:
                    return
                rowstride = int(rowstride)
                width, height = size.split(b'x')
                # TODO: see if there's any way to avoid casting to GLib.Bytes
                pxb = GdkPixbuf.Pixbuf.new_from_bytes(
                    GLib.Bytes.new(pixels), GdkPixbuf.Colorspace.RGB, False, 8,
                    int(width), int(height), rowstride)
                self.currentScreenshots[handle] = pxb
                self.cstore[i.path][C_PIXBUF] = pxb
                return
        # That handle is no longer in the cstore, remove it
        try:
            del self.currentScreenshots[handle]
        except:
            pass

    def getSelectedClients(self):
        selected = self.cview.get_selected_items()
        items = []
        for i in selected:
            items.append(self.cstore[i])
        return items

    def appendToGroupsMenu(self, group):
        mitem = Gtk.MenuItem(group.name)
        mitem.show()
        mitem.connect('activate', self.on_add_to_group_clicked, group)
        self.groups_menu.append(mitem)

    def removeFromGroupsMenu(self, group):
        mitem = Gtk.MenuItem(group.name)
        mitem.show()
        mitem.connect('activate', self.on_add_to_group_clicked, group)
        self.groups_menu.append(mitem)

    def changeHostname(self, mac, new_name):
        pass # FIXME: Implement this (virtual hostname)

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
        host = socket.gethostname()
        user = getpass.getuser()
        lang = locale.getlocale()[0]
        self.openLink("http://ts.sch.gr/repo/irc?user=%s&host=%s&lang=%s" % \
                       (user, host, lang))

    def iconsSizeScale_button_event(self, widget, event):
        """Make right click reset the thumbnail size.
        """
        if event.button == 3:
            self.iconsSizeScaleChanged(None, 120)
            self.reload_imagetypes()
            return True
        return False

    def reload_imagetypes(self):
        """Improve the quality of previously resized svg icons,
        by reloading them.
        """
        old_pixbufs = self.imagetypes.values()
        loadSVG = lambda path: GdkPixbuf.Pixbuf.new_from_file_at_size(
            path, self.scrWidth, self.scrHeight)
        self.imagetypes = {
            'offline': loadSVG('images/offline.svg'),
            'thin': loadSVG('images/thin.svg'),
            'fat': loadSVG('images/fat.svg'),
            'standalone': loadSVG('images/standalone.svg')
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
                    new_thumb = row[C_PIXBUF].scale_simple(
                        self.scrWidth, self.scrHeight,
                        GdkPixbuf.InterpType.NEAREST)
                    self.imagetypes[ctype] = new_thumb
                row[C_PIXBUF] = self.imagetypes[ctype]
            else:
                new_thumb = row[C_PIXBUF].scale_simple(
                    self.scrWidth, self.scrHeight,
                    GdkPixbuf.InterpType.NEAREST)
                row[C_PIXBUF] = new_thumb

        # Hack to remove the extra padding that remains after a 'zoom out'
        self.cview.set_resize_mode(Gtk.ResizeMode.IMMEDIATE)
        # TODO: Weird Gtk3 issue, they calculate excess width:
        # https://bugzilla.gnome.org/show_bug.cgi?id=680953
        # https://stackoverflow.com/questions/14090094/what-causes-the-different-display-behaviour-for-a-gtkiconview-between-different
        self.cview.get_cells()[0].set_fixed_size(width/4, -1)
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
                if clicked not in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()

            if widget is self.cview:
                menu = self.get('clients').get_submenu()

            menu.popup(None, None, None, None, event.button, event.time)
            menu.show()
            return True

    def on_clients_selection_changed(self, widget=None):
        selected = self.getSelectedClients()
        single_client = False
        if len(selected) == 1:
            single_client = True
        self.get('miClientProperties').set_sensitive(single_client)
        self.get('tb_client_properties').set_sensitive(single_client)

        if len(selected) > 0:
            self.get('miAddToGroup').set_sensitive(True)
            if not self.isDefaultGroupSelected():
                self.get('miRemoveFromGroup').set_sensitive(True)
            else:
                self.get('miRemoveFromGroup').set_sensitive(False)
        else:
            self.get('miAddToGroup').set_sensitive(False)
            self.get('miRemoveFromGroup').set_sensitive(False)

        if len(selected) > 1:
            self.get('statusbar_label').set_text(
                _('%d clients selected' % len(selected)))
        else:
            self.get('statusbar_label').set_text('')

    def execOnClients(self, command, clients=[], reply=None,
            mode=EM_SESSION_OR_SYSTEM, handles=[], warning='', params=None):
        # reply should be a method in which the result will be sent
        if params is None:
            params = []
        if len(self.cstore) == 0:
            # print('No clients')
            return False

        if isinstance(command, list) and len(command) > 0:
            command = '%s %s' %(command[0], ' '.join(
                [pipes.quote(str(x)) for x in command[1:]]))

        if (clients != [] or handles != []) and warning != '':
            if self.warnDlgPopup(warning) == False:
                return
        if clients == [] and handles != []:
            for handle in handles:
                cmd = self.daemon.command(handle, str(command))
                if reply:
                    cmd.addCallback(
                        lambda re, h=handle, p=params: reply(h, re, *p))
                    cmd.addErrback(lambda err: self.printErrors(
                        "when executing command %s on client %s: %s" %
                        (command,handle, err)))

        for client in clients:
            sent = False
            for em in mode:
                if em == EM_SESSION_ONLY:
                    handle = client[C_SESSION_HANDLE]
                elif em == EM_SYSTEM_ONLY:
                    handle = client[C_INSTANCE].hsystem
                else:  # em == EM_EXIT_IF_SENT
                    if sent:
                        break
                    else:
                        continue
                if handle == '':
                    continue
                sent = True
                cmd = self.daemon.command(handle, str(command))
                if reply:
                    cmd.addCallback(
                        lambda re, h=handle, p=params: reply(h, re, *p))
                    cmd.addErrback(lambda err: self.printErrors(
                        "when executing command %s on client %s: %s" %
                        (command,handle, err)))

    def execOnSelectedClients(
            self, command, reply=None, mode=EM_SESSION_OR_SYSTEM, warn=''):
        clients = self.getSelectedClients()
        if len(clients) == 0:  # No client selected, send the command to all
            clients = self.cstore
        else:  # Show the warning only when no clients are selected
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
        print('  **Twisted error:', error)
        return
