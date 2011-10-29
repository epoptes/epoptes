#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Common commands.
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

import os

class commands:
    """
    Define here all epoptes custom commands
    """

    def __init__(self):

        self.POWEROFF = './endsession --shutdown '
        self.REBOOT = './endsession --reboot '
        self.LOGOUT = './endsession --logout '
        self.EXEC = './execute '

        self.SCREENSHOT = 'if ./screenshot %i %i; \
                then BAD_SCREENSHOTS=0; elif [ "$BAD_SCREENSHOTS" = 3 ]; \
                then exit 1; else BAD_SCREENSHOTS=$(($BAD_SCREENSHOTS+1)); fi'

        self.EXEC_AMIXER = './execute amixer -c 0 -q sset Master '

        self.POWEROFF_WARN = _('Are you sure you want to shutdown all the computers?')
        self.REBOOT_WARN = _('Are you sure you want to reboot all the computers?')
        self.LOGOUT_WARN = _('Are you sure you want to log off all the users?')
        self.KILLALL_WARN = _('Are you sure you want to terminate all processes of the selected users?')

    def __setattr__(self, cmd, val):
        """
        Set new constants and prevent from changing values from already
        set constants
        """

        if hasattr(self, cmd):
            raise ValueError, 'Command %s is already set' % cmd

        self.__dict__[cmd] = val
