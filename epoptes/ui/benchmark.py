#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Network benchmark.
#
# Copyright (C) 2016 Fotis Tsamis <ftsamis@gmail.com>
# 2018, Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import os
import subprocess
import fcntl
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib
from twisted.internet import reactor

from graph import Graph
from epoptes.common.constants import *


def humanize(value, decimal=1, unit=''):
    value = float(value)
    for prefix in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(value) < 1000:
            value = round(value, decimal)
            return "%.*f %s%s" % (decimal, value, prefix, unit)
        value = value / 1000
    return "%.*f %s%s" % (decimal, value, 'Y', unit)


def bits_to_mbits(value):
    return float(value) / 1000 ** 2


def read_nonblocking(f):
        fd = f.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return f.read()
        except:
            return None


class NetworkBenchmark:
    def __init__(self, parent, clients, execute):
        self.wTree = Gtk.Builder()
        self.wTree.add_from_file('netbenchmark.ui')
        self.wTree.connect_signals(self)
        self.get = self.wTree.get_object
        self.parent = parent
        self.execute = execute
        self.clients_par = clients
        self.clients = {}
        self.iperf = None
        self.processes = {}
        self.results = {}
        self.dlg = self.get('benchmark_dialog')
        self.dlg.set_transient_for(self.parent)
        self.table = self.get('results_treeview')
        self.graph = None
        self.measurements_n = 0
        self.timeleft = 0
        self.timeout = 5
        self.output_timeout = None
        self.more_output = None

    def warning_message(self, msg):
        msgdlg = self.get('msgdlg')
        msgdlg.set_property("message-type", Gtk.MessageType.WARNING)
        msgdlg.set_transient_for(self.parent)
        msgdlg.set_title(_("Warning"))
        msgdlg.set_markup(msg)
        msgdlg.show_all()

    def error_message(self, msg):
        msgdlg = self.get('msgdlg')
        msgdlg.set_property("message-type", Gtk.MessageType.ERROR)
        msgdlg.set_transient_for(self.dlg)
        msgdlg.set_title(_("Error"))
        msgdlg.set_markup(msg)
        msgdlg.show_all()

    def on_message_dialog_close(self, widget):
        self.get('msgdlg').hide()

    def store_pid(self, handle, pid):
        """Store the PID of the iperf process running on each client
        allowing us to kill it later.
        """
        self.processes[handle] = int(pid)


    def create_graph(self, entries):
        options = {
            'axis': {
                'x': {
                    'ticks': [dict(v=i, label=l[0]) for i, l in enumerate(entries)],
                    'rotate': 0,
                    'label' : 'Computers'
                },
                'y': {
                    #'tickCount': 15,
                    'tickPrecision' : 0,
                    #'range' : [20,1100],
                    #'interval' : 10,
                    'label' : 'MBits/s',
                    'rotate': 0
                }
            },
            'background': {
                'chartColor': '#FBFBFB',
                'baseColor': '#FBFBFB',
                'lineColor': '#444446'
            },
            'colorScheme': {
                'name': 'rainbow',
                'args': {
                    'initialColor': 'green',
                },
            },
            'legend': {
                'position': {
                    'right': 20,
                    'top' : 20
                    }
            },
            'padding': {
                'left': 2,
                'right' : 20,
                'top' : 2,
                'bottom': 2
            },
            'title': _('Epoptes Network Benchmark Results')
        }

        dataSet = (
            (_('Upload Rate'), [[i, l[1]] for i, l in enumerate(entries)]),
            (_('Download Rate'), [[i, l[2]] for i, l in enumerate(entries)])
        )

        g = Graph()
        g.set_options(options)
        g.set_data(dataSet)
        height = len(entries)*50+100
        g.set_size_request(-1, height)
        return g


    def run(self):
        if not self.clients_par:
            self.warning_message(_('There are no selected clients to run the benchmark on.'))
            return False

        # Check if there are offline clients or clients with no root client in the selection
        off = []
        for client in self.clients_par:
            inst = client[C_INSTANCE]
            if inst.hsystem:
                self.clients[inst.hsystem.split(':')[0]] = (inst.hsystem, inst.get_name())
            else:
                off.append(inst.get_name())

        if not self.clients:
            self.warning_message(_('All of the selected clients are either offline, or do not have epoptes-client running as root.'))
            return False
        # Order matters here
        self.dlg.show()
        if off:
            self.warning_message(_('The following clients will be excluded from the benchmark because they are either offline, or do not have epoptes-client running as root.') + '\n\n' + ', '.join(off))


    def start_benchmark(self, seconds):
        self.iperf = subprocess.Popen('iperf -s -xS -yC'.split(), 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop_benchmark)
        for client in self.clients:
            handle = self.clients[client][0]
            d = self.execute(handle, 'start_benchmark %d' % seconds)
            d.addCallback(lambda r, h=client : self.store_pid(h, r))


    def stop_benchmark(self):
        for client in self.clients:
            break
            if client in self.processes:
                handle = self.clients[client][0]
                pid = self.processes[client]
                self.execute(handle, 'stop_benchmark %d' % pid)
        if self.iperf and self.iperf.poll() is None:
            self.iperf.kill()


    def on_btn_startBenchmark_clicked(self, widget):
        seconds = int(self.get('seconds_adjustment').get_value())
        # Half time for upload speed and half for download
        self.start_benchmark(seconds/2)
        self.timeleft = seconds
        self.get('seconds_spinbox').set_sensitive(False)
        self.get('hbox_buttons').set_visible(False)
        self.get('time_left_label').set_text(_("Benchmark finishing in %d seconds...") % self.timeleft)
        self.countdown_event = GLib.timeout_add(1000, self.update_time_left)
        self.get('hbox_status').set_visible(True)


    def update_time_left(self):
        self.timeleft -= 1
        # Check if the server has exited for some reason
        if self.iperf.poll() is not None:
            message = read_nonblocking(self.iperf.stderr)
            self.error_message(_("Something went wrong with the iperf server process:\n\n%s") % message)
            self.cancel_benchmark()
            return False
        
        if self.timeleft == 0:
            self.get('cancel_btn').set_visible(False)
            self.get('time_left_label').set_text(_("Processing data..."))
            self.get_results()
            return False
        self.get('time_left_label').set_text(_("Benchmark finishing in %d seconds...") % self.timeleft)
        return True


    def parse_iperf_output(self, output):
        """Parse 'output' as a string of single or multiple lines of CSV in the form of
        timestamp,server_ip,port,client_ip,port,id,from-to,transfered(Bytes),bandwidth(bps)
        and populate a dict of client_ip : [upload Mbps, download Mbps] pairs
        storing it in self.results.
        """
        data = output.strip().split()
        for line in data:
            values = line.split(',')
            if len(values) != 9:
                continue
            client_ip = values[3]
            client_port = values[4] # will be 5001 if the client is receiving
            bandwidth = int(values[8])
            if client_ip in self.clients:
                if client_ip not in self.results:
                    self.results[client_ip] = [0, 0]

                if client_port == "5001":
                    # Download (bits/s)
                    self.results[client_ip][1] = int(bandwidth)
                    self.measurements_n += 1
                else:
                    # Upload (bits/s)
                    self.results[client_ip][0] = int(bandwidth)
                    self.measurements_n += 1


    def get_more_output(self):
        output = read_nonblocking(self.iperf.stdout)
        if output:
            self.parse_iperf_output(output)
        if self.measurements_n == len(self.clients)*2:
            self.show_results()
            return False
        return True


    def get_results(self):
        self.more_output = GLib.timeout_add(200, self.get_more_output)
        self.output_timeout = GLib.timeout_add(self.timeout*1000, self.show_results, True)
        

    def data_func(self, column, cell, model, iter, index):
        bps = model[iter][index]
        if bps <= 0:
            cell.set_property("text", "—")
        else:
            cell.set_property("text", humanize(bps, unit='bps'))


    def show_results(self, timed_out=False):
        # At this point we either have all our output or we give up waiting
        self.stop_benchmark()
        if self.output_timeout:
            GLib.source_remove(self.output_timeout)
        if self.more_output:
            GLib.source_remove(self.more_output)
        
        upload_col = self.get('upload_column')
        download_col = self.get('download_column')
        upload_col.set_cell_data_func(self.get('cellrenderertext2'), self.data_func, 1)
        download_col.set_cell_data_func(self.get('cellrenderertext3'), self.data_func, 2)
        
        results_n = len(self.results)
        if results_n > 0:
            graph_entries = []
            total_up = 0
            total_down = 0
            # List all the clients regardless of if we received measurements
            for client_ip in self.clients:
                client_name = self.clients[client_ip][1]
                if client_ip in self.results:
                    up, down = self.results[client_ip]
                else:
                    up, down = (0,0)
                graph_entries.append((client_name, bits_to_mbits(up), bits_to_mbits(down)))
                self.get('results_store').append([client_name, up, down])
                total_up += up
                total_down += down
            
            self.graph = self.create_graph(graph_entries)
            self.graph.set_visible(True)
            self.dlg.set_visible(False)
            results_dlg = self.get('results_dialog')
            results_dlg.set_transient_for(self.parent)
            results_dlg.show_all()
            
            clients_n = len(self.clients)
            self.get('avg_client').set_text(humanize(total_up / clients_n, unit='bps'))
            self.get('total_client').set_text(humanize(total_up, unit='bps'))
            self.get('avg_server').set_text(humanize(total_down / clients_n, unit='bps'))
            self.get('total_server').set_text(humanize(total_down, unit='bps'))
            if timed_out:
                self.get('warning_hbox').show()
            else:
                self.get('warning_hbox').hide()
        else:
            self.error_message(_("Did not get measurements from any of the clients. Check your network settings."))
            self.dlg.set_visible(False)


    def cancel_benchmark(self):
        self.stop_benchmark()
        GLib.source_remove(self.countdown_event)
        self.get('hbox_status').set_visible(False)
        self.get('seconds_spinbox').set_sensitive(True)
        self.get('hbox_buttons').set_visible(True)


    def on_cancel_btn_clicked(self, widget):
        self.cancel_benchmark()


    def on_close_button_clicked(self, widget):
        self.get('results_dialog').destroy()


    def show_graph_toggled(self, widget):
        viewport = self.get('viewport')
        if viewport.get_child() == self.table:
            if self.graph:
                viewport.remove(self.table)
                viewport.add(self.graph)
        else:
            viewport.remove(self.graph)
            viewport.add(self.table)


    def on_btn_close_clicked(self, widget):
        self.dlg.destroy()


    def on_window_destroy(self, widget, event):
        self.dlg.destroy()

