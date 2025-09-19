#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2016-2025 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Network benchmark.
"""
from epoptes.common.constants import C_INSTANCE
from epoptes.core import spawn_process
from epoptes.ui.common import gettext as _, locate_resource
from gi.repository import GLib, Gtk


def humanize(value, decimal=1, unit=''):
    """Convert bits to [KMGTPEZ]bits."""
    value = float(value)
    for prefix in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(value) < 1000:
            value = round(value, decimal)
            return "%.*f %s%s" % (decimal, value, prefix, unit)
        value = value / 1000
    return "%.*f %s%s" % (decimal, value, 'Y', unit)


class Benchmark:
    """Network benchmark."""

    def __init__(self, parent, execute):
        self.clients = {}
        self.countdown_event = None
        self.execute = execute
        self.iperf = None
        self.parent = parent
        self.results = {}
        self.spawn_process = spawn_process.SpawnProcess(self.on_iperf_exit)
        self.timeleft = 0
        builder = Gtk.Builder()
        builder.add_from_file(locate_resource('benchmark.ui'))
        builder.connect_signals(self)
        self.dlg_message = builder.get_object('dlg_message')
        self.dlg_benchmark = builder.get_object('dlg_benchmark')
        self.adj_seconds = builder.get_object('adj_seconds')
        self.box_seconds = builder.get_object('box_seconds')
        self.spb_seconds = builder.get_object('spb_seconds')
        self.box_countdown = builder.get_object('box_countdown')
        self.lbl_countdown = builder.get_object('lbl_countdown')
        self.btn_start = builder.get_object('btn_start')
        self.btn_stop = builder.get_object('btn_stop')
        self.dlg_results = builder.get_object('dlg_results')
        self.lss_results = builder.get_object('lss_results')
        self.tvc_upload = builder.get_object('tvc_upload')
        self.tvc_download = builder.get_object('tvc_download')
        self.crt_upload = builder.get_object('crt_upload')
        self.crt_download = builder.get_object('crt_download')
        self.lbl_avg_down = builder.get_object('lbl_avg_down')
        self.lbl_avg_up = builder.get_object('lbl_avg_up')
        self.lbl_avg_down = builder.get_object('lbl_avg_down')
        self.lbl_avg_up = builder.get_object('lbl_avg_up')
        self.lbl_total_down = builder.get_object('lbl_total_down')
        self.lbl_total_up = builder.get_object('lbl_total_up')
        self.box_partial_results = builder.get_object('box_partial_results')
        self.dlg_message.set_transient_for(self.parent)
        self.dlg_benchmark.set_transient_for(self.parent)
        self.dlg_results.set_transient_for(self.parent)
        self.tvc_upload.set_cell_data_func(self.crt_upload, self.data_func, 1)
        self.tvc_download.set_cell_data_func(
            self.crt_download, self.data_func, 2)

    def warning_message(self, msg):
        """Show a warning dialog."""
        self.dlg_message.set_property("message-type", Gtk.MessageType.WARNING)
        self.dlg_message.set_title(_("Warning"))
        self.dlg_message.set_markup(msg)
        self.dlg_message.run()

    def error_message(self, msg):
        """Show an error dialog."""
        self.dlg_message.set_property("message-type", Gtk.MessageType.ERROR)
        self.dlg_message.set_title(_("Error"))
        self.dlg_message.set_markup(msg)
        self.dlg_message.run()

    def on_dlg_message_close(self, _widget, _event=None):
        """Handle btn_close_message.clicked and dlg_message.delete_event."""
        self.dlg_message.hide()

    def run(self, clients):
        """Show the dialog, then hide it so that it may be reused."""
        self.clients = {}
        # This can happen on an empty group.
        # Btw, "if not clients" is wrong as it's a Gtk.ListStore, not a dict.
        # pylint: disable=len-as-condition
        if len(clients) == 0:
            self.warning_message(
                _('There are no selected clients to run the benchmark on.'))
            return

        # Check if offline clients or clients with no root client are selected
        off = []
        for client in clients:
            inst = client[C_INSTANCE]
            if inst.hsystem:
                self.clients[inst.hsystem.split(':')[0]] =\
                    (inst.hsystem, inst.get_name())
            else:
                off.append(inst.get_name())

        # Now self.clients is the list of clients that can run the benchmark
        if not self.clients:
            self.warning_message(
                _('All of the selected clients are either offline,'
                  ' or do not have epoptes-client running as root.'))
            return
        if off:
            self.warning_message(
                _('The following clients will be excluded from the benchmark'
                  ' because they are either offline, or do not have'
                  ' epoptes-client running as root.')
                + '\n\n' + ', '.join(off))

        self.box_seconds.set_visible(True)
        self.box_countdown.set_visible(False)
        self.btn_start.set_visible(True)
        self.btn_stop.set_visible(False)
        self.dlg_benchmark.run()

    def on_btn_start_clicked(self, _widget):
        """Handle btn_start.clicked event."""
        seconds = int(self.adj_seconds.get_value())
        self.spawn_process.spawn('iperf -s -xS -yC'.split(),
                                 timeout=(seconds + 5),
                                 lines_max=2*len(self.clients))
        for client in self.clients:
            handle = self.clients[client][0]
            # Half time for upload speed and half for download
            self.execute(handle, 'start_benchmark "${GUI_IP}" %d' % seconds)
        self.timeleft = seconds
        self.box_seconds.set_visible(False)
        self.box_countdown.set_visible(True)
        self.btn_start.set_visible(False)
        self.btn_stop.set_visible(True)
        self.lbl_countdown.set_text(_("Benchmark finishing in %d seconds...")
                                    % self.timeleft)
        self.countdown_event = GLib.timeout_add(1000, self.update_countdown)

    def update_countdown(self):
        """Update the countdown label."""
        self.timeleft -= 1
        if self.timeleft >= 0:
            self.lbl_countdown.set_text(
                _("Benchmark finishing in %d seconds...") % self.timeleft)
        else:
            self.lbl_countdown.set_text(
                _("Some clients didn't respond in time!") + "\n"
                + _("Waiting for %d more seconds...") % (self.timeleft + 5))

        # Always recall; the timeout will be cancelled in on_iperf_exit.
        return True

    def parse_iperf_output(self, out_data):
        """Parse iperf CSV output and return a dict in the following form:
        result[client_ip] = [upload bps, download bps]
        """
        result = {}
        data = out_data.strip().split()
        for line in data:
            values = line.split(',')
            if len(values) != 9:
                continue
            _timestamp, src_ip, sport, dst_ip, _dport, _id, _interval, _tbytes, bbps = values
            bbps = int(bbps)
            if sport == '0':
                # Newer iperf versions also return the sum
                continue
            elif sport == '5001':
                client_ip = dst_ip
            else:
                client_ip = src_ip
            if client_ip in self.clients:
                if client_ip not in result:
                    result[client_ip] = [0, 0]
                if sport == "5001":
                    # upload bps (client to server)
                    result[client_ip][0] = bbps
                else:
                    # download bps (server to client)
                    result[client_ip][1] = bbps
        return result

    @staticmethod
    def data_func(_column, cell, model, itr, index):
        """Convert model's glong to text, to display humanized units."""
        bps = model[itr][index]
        if bps <= 0:
            cell.set_property("text", "—")
        else:
            cell.set_property("text", humanize(bps, unit='bps'))

    def on_iperf_exit(self, out_data, err_data, reason):
        """The benchmark has finished, show the results dialog."""
        GLib.source_remove(self.countdown_event)
        self.box_seconds.set_visible(True)
        self.box_countdown.set_visible(False)
        self.btn_start.set_visible(True)
        self.btn_stop.set_visible(False)

        if reason == "stopped":
            self.btn_stop.set_sensitive(True)
            return
        elif reason == "closed":
            return

        self.dlg_benchmark.hide()
        self.results = self.parse_iperf_output(out_data.decode("utf-8"))
        if not self.results:
            msg = _("Did not get measurements from any of the clients."
                    " Check your network settings.")
            if err_data:
                msg += "\n\n" + err_data.decode("utf-8")
            self.error_message(msg)
            return

        # At this point we do have some results, so show dlg_results
        total_up = 0
        total_down = 0
        self.lss_results.clear()
        # List all the clients regardless of if we received measurements
        for client_ip in self.clients:
            client_name = self.clients[client_ip][1]
            if client_ip in self.results:
                upload, download = self.results[client_ip]
            else:
                upload, download = (0, 0)
            self.lss_results.append([client_name, upload, download])
            total_up += upload
            total_down += download

        clients_n = len(self.clients)
        self.lbl_avg_up.set_text(
            humanize(total_up / clients_n, unit='bps'))
        self.lbl_total_up.set_text(humanize(total_up, unit='bps'))
        self.lbl_avg_down.set_text(
            humanize(total_down / clients_n, unit='bps'))
        self.lbl_total_down.set_text(humanize(total_down, unit='bps'))

        self.box_partial_results.set_visible(
            self.spawn_process.lines_count != 2*len(self.clients))
        self.dlg_results.run()

    def on_btn_stop_clicked(self, _widget):
        """Handle btn_stop.clicked event."""
        self.btn_stop.set_sensitive(False)
        self.spawn_process.stop('stopped')

    def on_dlg_benchmark_close(self, _widget, _event=None):
        """Handle btn_close_benchmark.clicked, dlg_benchmark.delete_event."""
        # For simplicity, we assume that the user isn't fast enough
        # to close the dialog and reopen it before on_exit is called.
        if self.spawn_process.state == "running":
            self.spawn_process.stop('stopped')
        self.dlg_benchmark.hide()

    def on_dlg_results_close(self, _widget, _event=None):
        """Handle btn_close_results.clicked and dlg_results.delete_event."""
        self.dlg_results.hide()
