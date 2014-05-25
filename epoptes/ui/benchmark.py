#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Network benchmark.
#
# Copyright (C) 2013 Fotis Tsamis <ftsamis@gmail.com>
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

import subprocess
import gtk
import gtk.gdk as gdk
import pygtk
import gobject
import cairo
import pycha.bar


from epoptes.common.constants import *


def createChart(lines, w, h):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)

    options = {
        'axis': {
            'x': {
                'ticks': [dict(v=i, label=l[0]) for i, l in enumerate(lines)],
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

    chart = pycha.bar.HorizontalBarChart(surface, options)

    dataSet = (
        (_('Upload Rate'), [[i, l[1]] for i, l in enumerate(lines)]),
        (_('Download Rate'), [[i, l[2]] for i, l in enumerate(lines)])
    )

    chart.addDataset(dataSet)
    chart.render()

    surface.flush()
    return surface



class NetworkBenchmark:
    def __init__(self, parent, clients, execute):
        self.wTree = gtk.Builder()
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
        self.timeleft = 0


    def warn(self, msg):
        warndlg = self.get('warndlg')
        warndlg.set_transient_for(self.dlg)
        warndlg.set_markup(msg)
        warndlg.show_all()

    def on_warn_close(self, widget):
        self.get('warndlg').hide()

    def reply(self, pid, handle):
        # This gets the PID of the iperf process running in the clients described by handle
        self.processes[handle] = int(pid)


    def run(self):
        if not self.clients_par:
            self.warn(_('There are no selected clients to run the benchmark on.'))
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
            self.warn(_('All of the selected clients are either offline, or do not have epoptes-client running as root.'))
            return False
        # Order matters here
        self.dlg.show()
        if off:
            self.warn(_('The following clients will be excluded from the benchmark because they are either offline, or do not have epoptes-client running as root.') + '\n\n' + ', '.join(off))
        


    def on_btn_startBenchmark_clicked(self, widget):
        seconds = int(self.get('seconds_adjustment').get_value())
        client_seconds = (seconds-5)/2 # Half time for upload speed and half for download
        self.timeleft = seconds
        self.get('seconds_spinbox').set_sensitive(False)
        self.get('hbox_buttons').set_visible(False)
        self.get('time_left_label').set_text(_("Benchmark finishing in %d seconds...") % self.timeleft)
        self.countdown_event = gobject.timeout_add(1000, self.update_time_left)
        self.get('hbox_status').set_visible(True)
        self.iperf = subprocess.Popen('iperf -s -xS -yC'.split(), stdout=subprocess.PIPE)

        for client in self.clients:
            d = self.execute(self.clients[client][0], 'background -p iperf -c $SERVER -r -t %d' % client_seconds)
            d.addCallback(lambda r, h=client: self.reply(r, h))


    def update_time_left(self):
        self.timeleft -= 1
        if self.timeleft == 0:
            self.get('cancel_btn').set_visible(False)
            self.get('time_left_label').set_text(_("Processing data..."))
            self.get_results()
            return False
        self.get('time_left_label').set_text(_("Benchmark finishing in %d seconds...") % self.timeleft)
        return True


    def kill_iperf_on_clients(self):
        for client, pid in self.processes.iteritems():
            self.execute(client, 'background kill -9 %d' % pid)


    def get_results(self):
        #timestamp,server_ip,sport,client_ip,cport,id,from-to,transfered(Bytes),bandwidth(bps)
        print 'Killing the iperf server'
        self.iperf.kill()
        string = self.iperf.stdout.read()
        self.kill_iperf_on_clients()
        #print "Output: '%s'" % string
        data = string.strip().split('\n')
        data = [line.split(',') for line in data]
        for line in data:
            if len(line) != 9:
                continue
            client = line[3]
            self.results[self.clients[client][1]] = [None, None] # Up, Down (Client)

        for line in data:
            client = line[3]
            bandwidth = int(line[8])

            # 5001 receives the data
            if line[4] == "5001":
                self.results[self.clients[client][1]][1] = round(float(bandwidth)/(1000**2), 1) # Download (Mbps)
            else:
                self.results[self.clients[client][1]][0] = round(float(bandwidth)/(1000**2), 1) # Upload (Mbps)

        graph_input = []
        total_up = 0
        total_down = 0
        for k, v in self.results.iteritems():
            graph_input.append((k, v[0], v[1]))
            self.get('results_store').append([k, int(v[0]), int(v[1])])
            total_up += v[0]
            total_down += v[1]
        clients=len(data)/2
        h=clients*50+100
        surface = createChart(graph_input, 498, h)
        data = surface.get_data()
        w, h, st = surface.get_width(), surface.get_height(), surface.get_stride()
        pixbuf = gdk.pixbuf_new_from_data(data, gtk.gdk.COLORSPACE_RGB, 1, 8, w,h,st)
        self.graph = gtk.image_new_from_pixbuf(pixbuf)
        self.graph.set_visible(True)
        self.dlg.set_visible(False)
        results_dlg = self.get('results_dialog')
        results_dlg.set_transient_for(self.parent)
        results_dlg.show_all()

        self.get('avg_client').set_text(str(round(total_up / clients, 1)) + ' Mbps')
        self.get('total_client').set_text(str(round(total_up, 1)) + ' Mbps')
        self.get('avg_server').set_text(str(round(total_down / clients, 1)) + ' Mbps')
        self.get('total_server').set_text(str(round(total_down, 1)) + ' Mbps')


    def on_cancel_btn_clicked(self, widget):
        # Kill the iperf processes on the clients
        self.kill_iperf_on_clients()
        self.iperf.kill()
        gobject.source_remove(self.countdown_event)
        self.get('hbox_status').set_visible(False)
        self.get('seconds_spinbox').set_sensitive(True)
        self.get('hbox_buttons').set_visible(True)


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

