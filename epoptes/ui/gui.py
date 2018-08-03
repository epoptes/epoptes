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
import random
import socket
import string

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
    """Epoptes GUI class."""
    def __init__(self):
        self.about = None
        self.benchmark = None
        self.client_information = None
        self.daemon = None
        self.exec_command = None
        self.labels_order = (1, 0)
        self.notify_queue = NotifyQueue(
            'Epoptes',
            '/usr/share/icons/hicolor/scalable/apps/epoptes.svg')
        self.send_message = None
        self.displayed_compatibility_warning = False
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

        # Hide the remote assistance menuitem if epoptes-client isn't installed
        if not os.path.isfile('/usr/share/epoptes-client/remote_assistance.py'):
            self.get('mi_remote_assistance').set_property('visible', False)
            self.get('smi_help_remote_support').set_property('visible', False)

        self.mnu_add_to_group = self.get('mnu_add_to_group')
        self.mni_add_to_group = self.get('mni_add_to_group')

        self.gstore = Gtk.ListStore(str, object, bool)

        self.trv_groups = self.get("trv_groups")
        self.trv_groups.set_model(self.gstore)
        self.trv_groups.get_selection().connect(
            "changed", self.on_group_selection_changed)

        self.mainwin = self.get('wnd_main')

        self.cstore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, object, str)
        self.icv_clients = self.get('icv_clients')
        self.set_labels_order(1, 0, None)

        self.icv_clients.set_model(self.cstore)
        self.icv_clients.set_pixbuf_column(C_PIXBUF)
        self.icv_clients.set_text_column(C_LABEL)

        self.cstore.set_sort_column_id(C_LABEL, Gtk.SortType.ASCENDING)
        self.on_icv_clients_selection_changed(None)

        self.icv_clients.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new("add", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.COPY)
        self.trv_groups.enable_model_drag_dest(
            [("add", Gtk.TargetFlags.SAME_APP, 0)], Gdk.DragAction.COPY)

        self.default_group = structs.Group('<b>'+_('Detected clients')+'</b>')
        default_iter = self.gstore.append(
            [self.default_group.name, self.default_group, False])
        self.default_group_ref = Gtk.TreeRowReference(
            self.gstore, self.gstore.get_path(default_iter))
        self.trv_groups.get_selection().select_path(
            self.default_group_ref.get_path())

        self.get('adj_icon_size').set_value(self.scrWidth)
        self.reload_imagetypes()

        saved_clients, groups = config.read_groups(
            os.path.expanduser('~/.config/epoptes/groups.json'))
        if len(groups) > 0:
            self.mni_add_to_group.set_sensitive(True)
        for group in groups:
            self.gstore.append([group.name, group, True])
            mitem = Gtk.MenuItem(label=group.name)
            mitem.show()
            # TODO: shouldn't mitem be the first parameter there?
            mitem.connect(
                'activate', self.on_imi_clients_add_to_group_activate, group)
            self.mnu_add_to_group.append(mitem)

        self.fill_icon_view(self.get_selected_group()[1])
        if config.settings.has_option('GUI', 'selected_group'):
            path = config.settings.getint('GUI', 'selected_group')
            self.trv_groups.get_selection().select_path(path)
        if config.settings.has_option('GUI', 'label'):
            mitem = self.get(config.settings.get('GUI', 'label'))
            if not mitem:
                mitem = self.get('rmi_labels_host_user')
            mitem.set_active(True)
        if config.settings.has_option('GUI', 'showRealNames'):
            self.get('cmi_show_real_names').set_active(
                config.settings.getboolean('GUI', 'showRealNames'))
        self.mainwin.set_sensitive(False)

    def save_settings(self):
        """Helper function for on_imi_file_quit_activate."""
        sel_group = self.gstore.get_path(self.get_selected_group()[0])[0]
        self.gstore.remove(self.gstore.get_iter(
            self.default_group_ref.get_path()))
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

    def on_imi_file_quit_activate(self, _widget):
        """Handle imi_file_quit.activate and wnd_main.destroy events."""
        self.save_settings()
        if self.vncserver is not None:
            self.vncserver.kill()
        if self.vncviewer is not None:
            self.vncviewer.kill()
        reactor.stop()

    def on_rmi_labels_host_user_toggled(self, rmi):
        """Handle rmi_labels_host_user.toggled event."""
        self.set_labels_order(1, 0, rmi)

    def on_rmi_labels_host_toggled(self, rmi):
        """Handle rmi_labels_host.toggled event."""
        self.set_labels_order(-1, 0, rmi)

    def on_rmi_labels_user_host_toggled(self, rmi):
        """Handle rmi_labels_user_host.toggled event."""
        self.set_labels_order(0, 1, rmi)

    def on_rmi_labels_user_toggled(self, rmi):
        """Handle rmi_labels_user.toggled event."""
        self.set_labels_order(0, -1, rmi)

    def set_labels_order(self, user_pos, name_pos, rmi):
        """Helper function for on_rmi_labels_*_toggled."""
        # Save the order so all new clients get the selected format
        if rmi:
            config.settings.set('GUI', 'label', Gtk.Buildable.get_name(rmi))
        self.labels_order = (user_pos, name_pos)
        for row in self.cstore:
            self.set_label(row)

    def on_cmi_show_real_names_toggled(self, widget):
        """Handle cmi_show_real_names.toggled event."""
        self.showRealNames = widget.get_active()
        for row in self.cstore:
            self.set_label(row)

    def on_imi_session_boot_activate(self, _widget):
        """Handle imi_session_boot.activate event."""
        clients = self.get_selected_clients()
        if len(clients) == 0:  # No client selected, send the command to all
            clients = self.cstore
        for client in clients:
            # Make sure that only offline computers will be sent to wol
            client = client[C_INSTANCE]
            if client.is_offline():
                wol.wake_on_lan(client.mac)

    def on_imi_session_logout_activate(self, _widget):
        """Handle imi_session_logout.activate event."""
        self.exec_on_selected_clients(
            ['logout'], mode=EM_SESSION,
            warn=_('Are you sure you want to log off all the users?'))

    def on_imi_session_reboot_activate(self, _widget):
        """Handle imi_session_reboot.activate event."""
        self.exec_on_selected_clients(
            ["reboot"],
            warn=_('Are you sure you want to reboot all the computers?'))

    def on_imi_session_shutdown_activate(self, _widget):
        """Handle imi_session_shutdown.activate event."""
        self.exec_on_selected_clients(
            ["shutdown"],
            warn=_('Are you sure you want to shutdown all the computers?'))

    @staticmethod
    def find_unused_port():
        """Find an unused port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port

    def reverse_connection(self, cmd, *args):
        """Helper function for on_imi_broadcasts_*_activate."""
        # Open vncviewer in listen mode
        if self.vncviewer is None or self.vncviewer.poll() is not None:
            self.vncviewerport = self.find_unused_port()
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
        self.exec_on_selected_clients([cmd, self.vncviewerport] + list(args))

    def on_imi_broadcasts_monitor_user_activate(self, _widget):
        """Handle imi_sbroadcasts_monitor_user.activate event."""
        self.reverse_connection('get_monitored')

    def on_imi_broadcasts_assist_user_activate(self, _widget):
        """Handle imi_sbroadcasts_assist_user.activate event."""
        if config.settings.has_option('GUI', 'grabkbdptr'):
            grab = config.settings.getboolean('GUI', 'grabkbdptr')
        if grab:
            self.reverse_connection('get_assisted', 'True')
        else:
            self.reverse_connection('get_assisted')

    def broadcast_screen(self, fullscreen=''):
        """Helper function for on_imi_broadcasts_broadcast_screen*_activate."""
        if self.vncserver is None:
            pwdfile = os.path.expanduser('~/.config/epoptes/vncpasswd')
            pwd = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            subprocess.call(['x11vnc', '-storepasswd', pwd, pwdfile])
            f = open(pwdfile, 'rb')
            pwd = f.read()
            f.close()
            self.pwd = ''.join('\\%o' % c for c in pwd)
            self.vncserverport = self.find_unused_port()
            self.vncserver = subprocess.Popen(
                ['x11vnc', '-noshm', '-nopw', '-quiet', '-viewonly', '-shared',
                 '-forever', '-nolookup', '-24to32', '-threads', '-rfbport',
                 str(self.vncserverport), '-rfbauth', pwdfile])
        # Running `xdg-screensaver reset` as root doesn't reset the D.E.
        # screensaver, so send the reset command to both epoptes processes
        self.exec_on_selected_clients(
            ['reset_screensaver'], mode=EM_SYSTEM_AND_SESSION)
        self.exec_on_selected_clients(
            ["receive_broadcast", self.vncserverport, self.pwd, fullscreen],
            mode=EM_SYSTEM_OR_SESSION)

    def on_imi_broadcasts_broadcast_screen_fullscreen_activate(self, _widget):
        """Handle imi_broadcasts_broadcast_screen_fullscreen.activate event."""
        self.broadcast_screen('true')

    def on_imi_broadcasts_broadcast_screen_windowed_activate(self, _widget):
        """Handle imi_broadcasts_broadcast_screen_windowed.activate event."""
        self.broadcast_screen('')

    def on_imi_broadcasts_stop_broadcasts_activate(self, _widget):
        """Handle imi_broadcasts_stop_broadcasts.activate event."""
        self.exec_on_clients(['stop_receptions'], self.cstore,
                             mode=EM_SYSTEM_AND_SESSION)
        if self.vncserver is not None:
            self.vncserver.kill()
            self.vncserver = None

    # TODO: Should we allow for running arbitrary commands in clients?
    def on_imi_execute_execute_command_activate(self, _widget):
        """Handle imi_execute_execute_command.activate event."""
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
        self.exec_on_selected_clients(['execute', cmd], mode=em)

    def on_imi_execute_send_message_activate(self, _widget):
        """Handle imi_execute_send_message.activate event."""
        if not self.send_message:
            self.send_message = SendMessage(self.mainwin)
        params = self.send_message.run()
        if params:
            self.exec_on_selected_clients(['message'] + list(params))

    def open_terminal(self, em):
        """Helper function for on_imi_open_terminal_*_activate."""
        clients = self.get_selected_clients()
        # If there is no client selected, send the command to all
        if len(clients) == 0:
            clients = self.cstore
        for client in clients:
            inst = client[C_INSTANCE]
            if inst.type == 'offline':
                continue
            port = self.find_unused_port()
            user = '--'
            if em == EM_SESSION and client[C_SESSION_HANDLE]:
                user = inst.users[client[C_SESSION_HANDLE]]['uname']
            elif em == EM_SYSTEM:
                user = 'root'
            title = '%s@%s' % (user, inst.get_name())
            subprocess.Popen(['xterm', '-T', title, '-e', 'socat',
                              'tcp-listen:%d,keepalive=1' % port,
                              'stdio,raw,echo=0'])
            self.exec_on_clients(['remote_term', port], [client], mode=em)

    def on_imi_open_terminal_user_locally_activate(self, _widget):
        """Handle imi_open_terminal_user_locally.activate event."""
        self.open_terminal(EM_SESSION)

    def on_imi_open_terminal_root_locally_activate(self, _widget):
        """Handle imi_open_terminal_root_locally.activate event."""
        self.open_terminal(EM_SYSTEM)

    def on_imi_open_terminal_root_remotely_activate(self, _widget):
        """Handle imi_open_terminal_root_remotely.activate event."""
        self.exec_on_selected_clients(['root_term'], mode=EM_SYSTEM)

    def on_imi_restrictions_lock_screen_activate(self, _widget):
        """Handle imi_restrictions_lock_screen.activate event."""
        msg = _("The screen is locked by a system administrator.")
        self.exec_on_selected_clients(['lock_screen', 0, msg])

    def on_imi_restrictions_unlock_screen_activate(self, _widget):
        """Handle imi_restrictions_unlock_screen.activate event."""
        self.exec_on_selected_clients(
            ['unlock_screen'], mode=EM_SESSION_AND_SYSTEM)

    def on_imi_restrictions_mute_sound_activate(self, _widget):
        """Handle imi_restrictions_mute_sound.activate event."""
        self.exec_on_selected_clients(
            ['mute_sound', 0], mode=EM_SYSTEM_OR_SESSION)

    def on_imi_restrictions_unmute_sound_activate(self, _widget):
        """Handle imi_restrictions_unmute_sound.activate event."""
        self.exec_on_selected_clients(
            ['unmute_sound'], mode=EM_SYSTEM_AND_SESSION)

    def on_imi_clients_add_to_group_activate(self, _widget, group):
        """Handle *dynamic* imi_clients_add_to_group.activate event."""
        clients = self.get_selected_clients()
        for client in clients:
            if not group.has_client(client[C_INSTANCE]):
                group.add_client(client[C_INSTANCE])

    def on_imi_clients_remove_from_group_activate(self, _widget):
        """Handle imi_clients_remove_from_group.activate event."""
        clients = self.get_selected_clients()
        group = self.get_selected_group()[1]
        if self.confirmation_dialog(
                _('Are you sure you want to remove the selected client(s)'
                  ' from group "%s"?') % group.name):
            for client in clients:
                group.remove_client(client[C_INSTANCE])
            self.fill_icon_view(self.get_selected_group()[1], True)

    def on_imi_clients_network_benchmark_activate(self, _widget):
        """Handle imi_clients_network_benchmark.activate event."""
        if not self.benchmark:
            self.benchmark = Benchmark(self.mainwin, self.daemon.command)
        self.benchmark.run(self.get_selected_clients() or self.cstore)

    def on_imi_clients_information_activate(self, _widget):
        """Handle imi_clients_information.activate event."""
        if not self.client_information:
            self.client_information = ClientInformation(self.mainwin)
        self.client_information.btn_edit_alias.set_sensitive(
            not self.is_default_group_selected())
        self.client_information.run(
            self.get_selected_clients()[0], self.daemon.command)
        self.set_label(self.get_selected_clients()[0])

    @staticmethod
    def open_url(link):
        """Helper function for on_imi_open_terminal_*_activate."""
        subprocess.Popen(["xdg-open", link])

    def on_imi_help_home_activate(self, _widget):
        """Handle imi_help_home.activate event."""
        self.open_url("http://www.epoptes.org")

    def on_imi_help_report_bug_activate(self, _widget):
        """Handle imi_help_report_bug.activate event."""
        self.open_url("https://bugs.launchpad.net/epoptes")

    def on_imi_help_ask_question_activate(self, _widget):
        """Handle imi_help_ask_question.activate event."""
        self.open_url("https://answers.launchpad.net/epoptes")

    def on_imi_help_translate_application_activate(self, _widget):
        """Handle imi_help_translate_application.activate event."""
        self.open_url("http://www.epoptes.org/translations")

    def on_imi_help_live_chat_irc_activate(self, _widget):
        """Handle imi_help_live_chat_irc.activate event."""
        host = socket.gethostname()
        user = getpass.getuser()
        lang = locale.getlocale()[0]
        self.open_url("http://ts.sch.gr/repo/irc?user=%s&host=%s&lang=%s" %
                      (user, host, lang))

    @staticmethod
    def on_imi_help_remote_support_activate(_widget):
        """Handle imi_help_remote_support.activate event."""
        subprocess.Popen('./remote_assistance.py',
                         cwd='/usr/share/epoptes-client')

    def on_imi_help_about_activate(self, _widget):
        """Handle imi_help_about_activate.activate event."""
        if not self.about:
            self.about = About(self.mainwin)
        self.about.run()

    def on_trv_groups_drag_drop(self, _wid, context, x, y, time):
        """Handle trv_groups.drag_drop event."""
        dest = self.trv_groups.get_dest_row_at_pos(x, y)
        if dest is not None:
            path, pos = dest
            group = self.gstore[path][G_INSTANCE]
            if group is not self.default_group:
                for cln in self.get_selected_clients():
                    cln = cln[C_INSTANCE]
                    if not group.has_client(cln):
                        group.add_client(cln)

        context.finish(True, False, time)
        return True

    def on_trv_groups_drag_motion(self, widget, context, x, y, etime):
        """Handle trv_groups.drag_motion event."""
        drag_info = widget.get_dest_row_at_pos(x, y)
        # Don't allow dropping in the empty space of the treeview,
        # or inside the 'Detected' group, or inside the currently selected group
        selected_path = self.gstore.get_path(self.get_selected_group()[0])
        if (not drag_info or drag_info[0] == self.default_group_ref.get_path()
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

    def on_crt_group_edited(self, _widget, path, new_name):
        """Handle crt_group.edited event."""
        self.gstore[path][G_LABEL] = new_name
        self.gstore[path][G_INSTANCE].name = new_name
        self.mnu_add_to_group.get_children()[int(path)-1].set_label(new_name)

    def set_move_group_sensitivity(self):
        """Helper function for on_btn_group_*_clicked."""
        selected = self.get_selected_group()
        selected_path = self.gstore.get_path(selected[0])[0]
        blocker = not selected[1] is self.default_group
        self.get('btn_group_up').set_sensitive(blocker and selected_path > 1)
        self.get('btn_group_down').set_sensitive(
            blocker and selected_path < len(self.gstore)-1)

    def on_btn_group_add_clicked(self, _widget):
        """Handle btn_group_add.clicked event."""
        new_group = structs.Group()
        itr = self.gstore.append([new_group.name, new_group, True])
        # Edit the name of the newly created group
        self.trv_groups.set_cursor(
            self.gstore.get_path(itr), self.get('tvc_group'), True)
        self.append_to_groups_menu(new_group)

    def on_btn_group_remove_clicked(self, _widget):
        """Handle btn_group_remove.clicked event."""
        group_iter = self.get_selected_group()[0]
        group = self.gstore[group_iter][G_INSTANCE]

        if self.confirmation_dialog(
                _('Are you sure you want to remove group "%s"?') % group.name):
            path = self.gstore.get_path(group_iter)[0]
            self.gstore.remove(group_iter)
            menuitem = self.mnu_add_to_group.get_children()[path-1]
            self.mnu_add_to_group.remove(menuitem)

    def on_btn_group_up_clicked(self, _widget):
        """Handle btn_group_up.clicked event."""
        selected_group_iter = self.get_selected_group()[0]
        path = self.gstore.get_path(selected_group_iter)[0]
        previous_iter = self.gstore.get_iter(path-1)
        self.gstore.swap(selected_group_iter, previous_iter)
        self.set_move_group_sensitivity()
        mitem = self.mnu_add_to_group.get_children()[path-1]
        self.mnu_add_to_group.reorder_child(mitem, path-2)

    def on_btn_group_down_clicked(self, _widget):
        """Handle btn_group_down.clicked event."""
        selected_group_iter = self.get_selected_group()[0]
        path = self.gstore.get_path(selected_group_iter)[0]
        self.gstore.swap(selected_group_iter,
                         self.gstore.iter_next(selected_group_iter))
        self.set_move_group_sensitivity()
        mitem = self.mnu_add_to_group.get_children()[path-1]
        self.mnu_add_to_group.reorder_child(mitem, path)

    def on_icv_clients_selection_changed(self, _widget):
        """Handle icv_clients.selection_changed event."""
        selected = self.get_selected_clients()
        single_client = False
        if len(selected) == 1:
            single_client = True
        self.get('imi_clients_information').set_sensitive(single_client)
        self.get('tlb_clients_information').set_sensitive(single_client)

        if len(selected) > 0:
            self.get('mni_add_to_group').set_sensitive(True)
            self.get('imi_clients_remove_from_group').set_sensitive(
                not self.is_default_group_selected())
        else:
            self.get('mni_add_to_group').set_sensitive(False)
            self.get('imi_clients_remove_from_group').set_sensitive(False)

        if len(selected) > 1:
            self.get('lbl_status').set_text(
                _('%d clients selected' % len(selected)))
        else:
            self.get('lbl_status').set_text('')

    def on_icv_clients_button_press_event(self, widget, event):
        """Handle icv_clients.button_press event."""
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))

        if event.button == 3:
            if widget is self.icv_clients:
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

            if widget is self.icv_clients:
                menu = self.get('mni_clients').get_submenu()

            menu.popup(None, None, None, None, event.button, event.time)
            menu.show()
            return True

    def reload_imagetypes(self):
        """Helper function for on_btn_size_* and on_scl_icon_size_*.
        Improve the quality of previously resized svg icons, by reloading them.
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

    def on_btn_size_down_clicked(self, _widget):
        """Handle btn_size_down.clicked event."""
        adj = self.get('adj_icon_size')
        adj.set_value(adj.get_value() - 15)
        self.reload_imagetypes()

    def on_btn_size_up_clicked(self, _widget):
        """Handle btn_size_up.clicked event."""
        adj = self.get('adj_icon_size')
        adj.set_value(adj.get_value() + 15)
        self.reload_imagetypes()

    def on_scl_icon_size_value_changed(self, _widget, width=None):
        """Handle scl_icon_size_value.changed event."""
        adj = self.get('adj_icon_size')
        if width:
            adj.set_value(width)
        else:
            width = adj.get_value()
        self.scrWidth = int(width)
        self.scrHeight = int(3*self.scrWidth/4)  # Κeep the 4:3 aspect ratio

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
        self.icv_clients.set_resize_mode(Gtk.ResizeMode.IMMEDIATE)
        # TODO: Weird Gtk3 issue, they calculate excess width:
        # https://bugzilla.gnome.org/show_bug.cgi?id=680953
        # https://stackoverflow.com/questions/14090094/what-causes-the-different-display-behaviour-for-a-gtkiconview-between-different
        self.icv_clients.get_cells()[0].set_fixed_size(width/4, -1)
        self.icv_clients.check_resize()

    def on_scl_icon_size_button_press_event(self, _widget, event):
        """Make right click reset the thumbnail size."""
        if event.button == 3:
            self.on_scl_icon_size_value_changed(None, 120)
            self.reload_imagetypes()
            return True
        return False

    def on_scl_icon_size_button_release_event(self, _widget, _event):
        """Handle scl_icon_size.button_release event."""
        # Here we want to resize the SVG icons from imagetypes at a better
        # quality than this of the quick pixbuf scale, since we assume that
        # the user has decided the desired zoom level.
        self.reload_imagetypes()

    # TODO: this is callback from uiconnection.py
    def connected(self, daemon):
        self.mainwin.set_sensitive(True)
        self.daemon = daemon
        daemon.enumerate_clients().addCallback(lambda h: self.amp_got_clients(h))
        self.fill_icon_view(self.get_selected_group()[1])

    def disconnected(self, _daemon):
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
        d.addCallback(lambda r: self.add_client(handle, r.decode()))
        d.addErrback(lambda err: self.print_errors(
            "when connecting client %s: %s" % (handle, err)))

    def amp_client_disconnected(self, handle):
        print("Disconnect from", handle)

        def determine_offline(client):
            if client.hsystem == '' and client.users == {}:
                client.set_offline()
        client = None
        for client in structs.clients:
            if client.hsystem == handle:
                if self.get_selected_group()[1].has_client(client) \
                        or self.is_default_group_selected():
                    self.notify_queue.enqueue(
                        _("Shut down:"), client.get_name())
                client.hsystem = ''
                determine_offline(client)
                break

            elif handle in client.users:
                if self.get_selected_group()[1].has_client(client) \
                        or self.is_default_group_selected():
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

        if client is not None:
            for row in self.cstore:
                if row[C_INSTANCE] is client:
                    self.fill_icon_view(self.get_selected_group()[1], True)
                    break

    def amp_got_clients(self, handles):
        print("Got clients:", ', '.join(handles) or 'None')
        for handle in handles:
            d = self.daemon.command(handle, 'info')
            d.addCallback(
                lambda r, h=handle: self.add_client(h, r.decode(), True))
            d.addErrback(lambda err: self.print_errors(
                "when enumerating client %s: %s" % (handle, err)))

    def on_group_selection_changed(self, _treeselection):
        self.cstore.clear()
        selected = self.get_selected_group()

        if selected is not None:
            self.fill_icon_view(selected[1])
            path = self.gstore.get_path(selected[0])[0]
            self.mnu_add_to_group.foreach(lambda w: w.set_sensitive(True))
            menuitems = self.mnu_add_to_group.get_children()
            if path != 0 and path-1 < len(menuitems):
                menuitems[path-1].set_sensitive(False)
        else:
            if not self.default_group_ref.valid():
                return
            self.trv_groups.get_selection().select_path(
                self.default_group_ref.get_path())
        self.get('btn_group_remove').set_sensitive(
            not self.is_default_group_selected())
        self.set_move_group_sensitivity()

    def add_to_icon_view(self, client):
        """Properly add a Client class instance to the clients iconview."""
        # If there are one or more users on client, add a new iconview entry
        # for each one of them.
        label = 'uname'
        if self.showRealNames:
                label = 'rname'
        if client.users:
            for hsession, user in client.users.items():
                self.cstore.append(
                    [self.calculate_label(client, user[label]),
                     self.imagetypes[client.type], client, hsession])
                self.ask_thumbshot(hsession, True)
        else:
            self.cstore.append(
                [self.calculate_label(client),
                 self.imagetypes[client.type], client, ''])

    def fill_icon_view(self, group, keep_selection=False):
        """Fill the clients iconview from a Group class instance."""
        if keep_selection:
            selection = [row[C_INSTANCE] for row in self.get_selected_clients()]
        self.cstore.clear()
        if self.is_default_group_selected():
            clients_list = [client for client in structs.clients
                            if client.type != 'offline']
        else:
            clients_list = group.get_members()
        # Add the new clients to the iconview
        for client in clients_list:
            self.add_to_icon_view(client)
        if keep_selection:
            for row in self.cstore:
                if row[C_INSTANCE] in selection:
                    self.icv_clients.select_path(row.path)
                    selection.remove(row[C_INSTANCE])

    def is_default_group_selected(self):
        """Return True if the default group is selected"""
        if self.get_selected_group():
            return self.get_selected_group()[1] is self.default_group
        return True

    def get_selected_group(self):
        """Return a 2-tuple containing the itr and the instance
        for the currently selected group."""
        itr = self.trv_groups.get_selection().get_selected()[1]
        if itr:
            return itr, self.gstore[itr][G_INSTANCE]
        else:
            return None

    def add_client(self, handle, r, already=False):
        # already is True if the client was started before epoptes
        print("add_client's been called for", handle)
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
            self.daemon.command(
                handle, "die 'Incompatible Epoptes server version!'")
            if not self.displayed_compatibility_warning:
                self.displayed_compatibility_warning = True
                self.warning_dialog(_(
                    """A connection attempt was made by a client with"""
                    """ version %s, which is incompatible with the current"""
                    """ epoptes version.\n\nYou need to update your clients"""
                    """ to the latest epoptes-client version.""") % version)
            return False
        sel_group = self.get_selected_group()[1]
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
                                or self.is_default_group_selected()):
                self.notify_queue.enqueue(
                    _("Connected:"),
                    _("%(user)s on %(host)s") % {"user": user, "host": host})

        if sel_group.has_client(client) or self.is_default_group_selected():
            self.fill_icon_view(sel_group, True)

    def set_label(self, row):
        inst = row[C_INSTANCE]
        if row[C_SESSION_HANDLE]:
            label = 'uname'
            if self.showRealNames:
                label = 'rname'
            user = row[C_INSTANCE].users[row[C_SESSION_HANDLE]][label]
        else:
            user = ''
        row[C_LABEL] = self.calculate_label(inst, user)

    def calculate_label(self, client, username=''):
        """Return the iconview label from a hostname/alias
        and a username, according to the user options.
        """
        user_pos, name_pos = self.labels_order

        alias = client.get_name()
        if username == '' or user_pos == -1:
            return alias
        else:
            if user_pos == 0:
                label = username
                if name_pos == 1:
                    label += " (%s)" % alias
            else:  # name_pos == 0
                label = alias
                if user_pos == 1:
                    label += " (%s)" % username
            return label

    def ask_thumbshot(self, handle, first_time=False):
        # Should always return False to prevent glib from calling us again
        if first_time:
            if handle not in self.currentScreenshots:
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
        # of searching the whole model (Need to modify exec_on_clients)
        for client in self.cstore:
            if handle == client[C_SESSION_HANDLE]:
                # TODO: rename "thumbnail" and "screenshot" to "thumbshot"
                self.exec_on_clients(
                    ['thumbshot', self.scrWidth, self.scrHeight],
                    handles=[handle], reply=self.got_thumbshot)
                return False
        # That handle is no longer in the cstore, remove it
        try:
            del self.currentScreenshots[handle]
        except:
            pass
        return False

    def got_thumbshot(self, handle, reply):
        for i in self.cstore:
            if handle == i[C_SESSION_HANDLE]:
                # We want to ask for thumbshots every 5 sec after the last one.
                # So if the client is too stressed and needs 7 secs to
                # send a thumbshot, we'll ask for one every 12 secs.
                GLib.timeout_add(5000, self.ask_thumbshot, handle)
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

    def get_selected_clients(self):
        selected = self.icv_clients.get_selected_items()
        items = []
        for i in selected:
            items.append(self.cstore[i])
        return items

    def append_to_groups_menu(self, group):
        mitem = Gtk.MenuItem(group.name)
        mitem.show()
        mitem.connect(
            'activate', self.on_imi_clients_add_to_group_activate, group)
        self.mnu_add_to_group.append(mitem)

    def remove_from_groups_menu(self, group):
        mitem = Gtk.MenuItem(group.name)
        mitem.show()
        mitem.connect(
            'activate', self.on_imi_clients_add_to_group_activate, group)
        self.mnu_add_to_group.append(mitem)

    def exec_on_clients(
            self, command, clients=[], reply=None, mode=EM_SESSION_OR_SYSTEM,
            handles=[], warning='', params=None):
        # reply should be a method in which the result will be sent
        if params is None:
            params = []
        if len(self.cstore) == 0:
            # print('No clients')
            return False

        if isinstance(command, list) and len(command) > 0:
            command = '%s %s' % (command[0], ' '.join(
                [pipes.quote(str(x)) for x in command[1:]]))

        if (clients != [] or handles != []) and warning != '':
            if not self.confirmation_dialog(warning):
                return
        if clients == [] and handles != []:
            for handle in handles:
                cmd = self.daemon.command(handle, str(command))
                # TODO: do we need callbacks even when no reply?
                if reply:
                    cmd.addCallback(
                        lambda r, h=handle, p=params: reply(h, r, *p))
                    cmd.addErrback(lambda err: self.print_errors(
                        "when executing command %s on client %s: %s" %
                        (command, handle, err)))

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
                # TODO: do we need callbacks even when no reply?
                if reply:
                    cmd.addCallback(
                        lambda r, h=handle, p=params: reply(h, r, *p))
                    cmd.addErrback(lambda err: self.print_errors(
                        "when executing command %s on client %s: %s" %
                        (command, handle, err)))

    def exec_on_selected_clients(
            self, command, reply=None, mode=EM_SESSION_OR_SYSTEM, warn=''):
        clients = self.get_selected_clients()
        if len(clients) == 0:  # No client selected, send the command to all
            clients = self.cstore
        else:  # Show the warning only when no clients are selected
            warn = ''
        self.exec_on_clients(command, clients, reply, mode, warning=warn)

    def confirmation_dialog(self, text):
        dlg = Gtk.MessageDialog(
            self.mainwin, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO,
            text, title=_('Confirm action'))
        resp = dlg.run()
        dlg.destroy()
        return resp == Gtk.ResponseType.YES

    def warning_dialog(self, text):
        dlg = Gtk.MessageDialog(
            self.mainwin, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.CLOSE,
            text, title=_('Warning'))
        dlg.run()
        dlg.destroy()

    @staticmethod
    def print_errors(error):
        print('  **Twisted error:', error)
        return
