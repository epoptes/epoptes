#!/usr/bin/python3
# This file is part of Epoptes, http://epoptes.org
# Copyright 2012-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Reverse screen sharing using VNC or GNU screen and socat.
"""
import os
import signal
import subprocess

from _common import gettext as _
from gi.repository import GLib, Gtk


class RemoteAssistance:
    """Reverse screen sharing using VNC or GNU screen and socat."""
    def __init__(self, from_main=False):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('remote_assistance.ui')

        self.btn_action = self.builder.get_object('btn_action')
        self.cmb_method = self.builder.get_object('cmb_method')
        self.ent_host = self.builder.get_object('ent_host')
        self.icn_status = self.builder.get_object('icn_status')
        self.lbl_status = self.builder.get_object('lbl_status')
        self.spn_status = self.builder.get_object('spn_status')
        self.wnd_support = self.builder.get_object('wnd_support')

        self.from_main = from_main
        self.retry_timeout_id = None
        self.retry = False
        self.retry_interval = 10
        self.manually_stopped = False
        self.proc = None
        self.host = ''
        self.connected = False

        self.builder.connect_signals(self)
        signal.signal(signal.SIGUSR1, self.on_sigusr1)
        self.wnd_support.show()

    def connect(self):
        """Handle btn_action clicked when it's in the Connect state."""
        self.host = self.ent_host.get_text().strip()
        pid = os.getpid()

        share_terminal = self.cmb_method.get_active() != 0
        if share_terminal:
            cmd = ['xterm', '-e', os.path.dirname(__file__) +
                   '/share-terminal', self.host]
            subprocess.Popen(cmd)
            self.on_btn_close_clicked(None)
            return

        cmd = ['x11vnc', '-q', '-nopw', '-connect_or_exit', self.host,
               '-afteraccept', 'kill -USR1 {}'.format(pid)]
        self.proc = subprocess.Popen(cmd)

        # Set the status as "Connecting"
        if self.retry_timeout_id:
            GLib.source_remove(self.retry_timeout_id)
            self.retry_timeout_id = None
        self.set_state('connecting')

        # Start polling the process every 1 second to see if it's still alive
        GLib.timeout_add(1000, self.poll_process)

    def disconnect(self):
        """Handle btn_action clicked when it's in the Disconnect state."""
        self.manually_stopped = True
        if self.retry_timeout_id is not None:
            self.set_state('disconnected')
            GLib.source_remove(self.retry_timeout_id)
            self.retry_timeout_id = None
        if self.proc:
            self.proc.kill()
        self.btn_action.set_label(Gtk.STOCK_CONNECT)

    def poll_process(self):
        """Continuously check if the spawned process has terminated."""
        # If process has not terminated yet return True to continue the timeout
        if self.proc.poll() is None:
            return True
        else:
            # Check if it disconnected or failed and call the correct signal
            if self.connected:
                self.set_state('disconnected')
                if self.retry and not self.manually_stopped:
                    self.update_and_retry(_('Not connected'),
                                          self.retry_interval)
                    self.btn_action.set_label(Gtk.STOCK_DISCONNECT)
                    self.manually_stopped = True
                else:
                    self.btn_action.set_label(Gtk.STOCK_CONNECT)
                self.connected = False
            else:
                self.set_state('failed')
            self.proc = None
            return False

    def set_state(self, state):
        """Update the UI to match the new state."""
        # Stop the spinner
        self.spn_status.stop()
        self.spn_status.hide()
        self.icn_status.show()

        if state == 'connecting':
            # Start the spinner
            self.icn_status.hide()
            self.spn_status.show()
            self.spn_status.start()
            self.lbl_status.set_text(_('Connecting to %s...') % self.host)
            self.btn_action.set_label(Gtk.STOCK_DISCONNECT)
        elif state == 'connected':
            self.connected = True
            self.icn_status.set_from_stock(Gtk.STOCK_YES, Gtk.IconSize.BUTTON)
            self.lbl_status.set_text(_('Connected to %s') % self.host)
            self.btn_action.set_label(Gtk.STOCK_DISCONNECT)
        elif state == 'disconnected':
            msg = _('Not connected')
            self.icn_status.set_from_stock(Gtk.STOCK_NO, Gtk.IconSize.BUTTON)
            self.lbl_status.set_text(msg)
        elif state == 'failed':
            msg = _('Failed to connect to %s') % self.host
            self.lbl_status.set_text(msg)
            self.icn_status.set_from_stock(
                Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.BUTTON)

            if self.retry:
                self.update_and_retry(msg, self.retry_interval)
                self.btn_action.set_label(Gtk.STOCK_DISCONNECT)
            else:
                self.btn_action.set_label(Gtk.STOCK_CONNECT)

    def update_and_retry(self, msg, interval):
        """Show a "Retrying in 10..." label, and then retry."""
        if interval == 0:
            self.on_btn_action_clicked(None)
        else:
            self.lbl_status.set_text(
                msg + ' ' + _('Retrying in %d...') % interval)
            self.retry_timeout_id = GLib.timeout_add(
                1000, self.update_and_retry, msg, interval - 1)
        return False

    def on_btn_action_clicked(self, _widget):
        """Handle btn_action clicked event."""
        if self.btn_action.get_label() == Gtk.STOCK_CONNECT:
            self.connect()
        else:
            self.disconnect()

    def on_btn_close_clicked(self, _widget):
        """Handle btn_close clicked event."""
        if self.proc:
            self.disconnect()
        if self.from_main:
            Gtk.main_quit()

    def on_chb_reconnect_toggled(self, _widget):
        """Handle chb_reconnect toggled event."""
        self.retry = not self.retry

    def on_ent_host_changed(self, widget):
        """Handle ent_host changed event."""
        txt = widget.get_text().strip()
        if self.btn_action.get_label() == Gtk.STOCK_CONNECT:
            self.btn_action.set_property('sensitive', txt != "")

    def on_sigusr1(self, _signum, _frame):
        """Handle SIGUSR1 (successful connection) event."""
        self.set_state('connected')

    def on_wnd_support_delete_event(self, _widget, _event):
        """Handle wnd_support delete event."""
        self.on_btn_close_clicked(None)


def main():
    """Run the module from the command line."""
    RemoteAssistance(True)
    Gtk.main()


if __name__ == '__main__':
    main()
