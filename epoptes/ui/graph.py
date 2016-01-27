#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Graph generator.
#
# Copyright (C) 2016 Fotis Tsamis <ftsamis@gmail.com>
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

import gtk
import cairo
from pycha.bar import HorizontalBarChart

class Graph(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose-event", self.expose)
        self.connect("size-allocate", self.size_allocate)
        self._surface = None
        self._options = None
 
    def set_options(self, options):
        self._options = options
 
    def set_data(self, data):
        self._data = data
        self.queue_draw()
 
    def plot(self):
        chart = HorizontalBarChart(self._surface, self._options)
        chart.addDataset(self._data)
        chart.render()
 
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        return False
 
    def draw(self, context):
        rect = self.get_allocation()
        self._surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                           rect.width, rect.height)
        self.plot()
        context.set_source_surface(self._surface, 0, 0)
        context.paint()
 
    def size_allocate(self, widget, requisition):
        self.queue_draw()

