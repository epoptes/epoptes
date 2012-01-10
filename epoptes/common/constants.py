#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Common constants.
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

# Warn users to update their chroots if they have a lower epoptes-client version 
# than this
COMPATIBILITY_VERSION = [0, 1]

# ['ltsp123', '00-1b-24-89-65-d6', '127.0.0.1:46827', '10.160.31.126:44920', 
#  'thin', 'user3', <gtk.gdk.Pixbuf>, '10.160.31.123', 'user (ltsp123)']
C_LABEL = 0
C_PIXBUF = 1
C_INSTANCE = 2
C_SESSION_HANDLE = 3
# [label, <gtk.gdk.Pixbuf>, <Client instance>, username]
G_LABEL = 0
G_INSTANCE = 1

class Constants:
    """
    Define here all constants 
    """
    
    ZENITY_INFO = 'zenity --info '
    ZENITY_WARNING = 'zenity --warning '
    ZENITY_ERROR = 'zenity --error '

    HOME_DIR = '/home/'
    HOME_PREFIX = '~/'
    XDG_DOCUMENTS_DIR = 'Documents'
    GROUP_PAT = '{g}'
    MAX_DIRS = 50

    MODE_R = 0744
    MODE_W = 0733
    MODE_RW = 0766

    EXISTS = 1
    NOT_EXISTS = 0

    SEND = 0
    RECEIVE = 1
    
    
    def __setattr__(self, attribute, val):
        """
        Set new constants and prevent from changing values from already
        set constants
        """

        if hasattr(self, attribute):
            raise ValueError, 'Constant %s already has a value' % attribute

        self.__dict__[attribute] = val
