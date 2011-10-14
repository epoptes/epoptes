# -*- coding: utf-8 -*-

###########################################################################
# Configuration file parser and other default configuration variables.
#
# Copyright (C) 2011 Alkis Georgopoulos <alkisg@gmail.com>
# Copyright (C) 2011 Fotis Tsamis <alkisg@gmail.com>
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
import ConfigParser

def read_plain_file(filename):
    """Return the whole contents of a plain text file into a string list.

    If the file doesn't exist or isn't readable, return an empty list.
    Also sort the contents and merge duplicate entries.
    """

    if not os.path.isfile(filename):
        return []
    try:
        f = open(filename, 'r')
        contents = [ x.strip() for x in f.readlines()]
        f.close()
        return contents
    except:
        return []


def write_plain_file(filename, contents):
    """Write the contents string list to filename. Return True if successful.
    """

    try:
        if not os.path.isdir(path):
            os.mkdir(path)
        f = open(filename, 'w')
        f.write(writelines([ x + '\n' for x in contents ]))
        return True
    except:
        return False


def read_ini_file(filename):
    """Return a ConfigParser from the contents of a configuration file.
    """
    conf = ConfigParser.ConfigParser()
    try:
        conf.read(filename)
    except:
        pass
    return conf


def write_ini_file(filename, contents):
    """Write contents to a ConfigParser file. Return True if successful.
    """
    conf = ConfigParser.ConfigParser()
    try:
        conf.write(filename)
        return True
    except:
        return False


def read_shell_file(filename):
    """Return the variables of a shell-like configuration file in a dict.

    If the file doesn't exist or isn't readable, return an empty list.
    Also strip all comments, if any.
    """
    
    if not os.path.isfile(filename):
        return []
    try:
        f = open(filename, 'r')
        contents = f.read()
        f.close()
        contents = shlex.split(contents, True)
        # TODO: maybe return at least all the valid pairs?
        return dict(v.split('=') for v in contents)
    except:
        return []


# The system settings are shared with epoptes-clients, that's why the caps.
system = read_shell_file('/etc/default/epoptes')
system.setdefault('PORT', 569)
system.setdefault('SOCKET_GROUP', 'admin')
system.setdefault('DIR', '/var/run/epoptes')

if os.getuid() != 0:
    path = os.path.expanduser('~/.config/epoptes/')
    if not os.path.isdir(path):
        os.mkdir(path)
    
    settings_file = os.path.join(path, 'settings')
    if not os.path.isfile(settings_file):
        _settings = open(settings_file, 'w')
        _settings.write('[GUI]\n#thumbnails_width=200\n#thumbnails_height=150')
        _settings.close()
    
    settings = read_ini_file(settings_file)
    user = {}
    if settings.has_option('GUI', 'thumbnails_width'):
        user['thumbnails_width'] = settings.getint('GUI', 'thumbnails_width')
    if settings.has_option('GUI', 'thumbnails_height'):
        user['thumbnails_height'] = settings.getint('GUI', 'thumbnails_height')
    history = sorted(list(set(read_shell_file(os.path.join(path, 'history')))))


# For debugging reasons, if ran from command line, dump the config
if __name__ == '__main__':
    print system

