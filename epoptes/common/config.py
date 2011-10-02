# -*- coding: utf-8 -*-

###########################################################################
# Configuration file parser and other default configuration variables.
#
# Copyright (C) 2011 Alkis Georgopoulos <alkisg@gmail.com>
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
import shlex

def read_system_config(path):
    """Return the variables of a shell-like file in a dict.

    If the file doesn't exist or isn't readable, return an empty list.
    Also strip all comments, if any.
    """
    
    if not os.path.isfile(path):
        return []
    try:
        f = open(path, 'r')
        contents = f.read()
        f.close()
        contents = shlex.split(contents, True)
        # TODO: maybe return at least all the valid pairs?
        return dict(v.split('=') for v in contents)
    except:
        return []

def read_user_config(path):
    """Return the variables of a configuration file in a dict.
    """

def write_user_config(path):
    """Write the contents of the "user" dict to the configuration file.
    """

system = read_system_config('/etc/default/epoptes')
system.setdefault('PORT', 569)
system.setdefault('SOCKET_GROUP', 'admin')
system['DIR'] = '/var/run/epoptes'

#user = read_user_config('$HOME/.config/ktl')

# For debugging reasons, if ran from command line, dump the config
if __name__ == '__main__':
    print system

