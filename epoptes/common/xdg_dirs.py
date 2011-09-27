#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Utility functions to get a user's localized XDG directories.
#
# Copyright (C) 2010 Alkis Georgopoulos <alkisg@gmail.com>
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
import pwd
import shlex
import gettext

domain = "xdg-user-dirs"
gettext.bindtextdomain(domain)
gettext.textdomain(domain)
T_ = gettext.gettext


def read_config_file(path):
    """Return the contents of a shell-like file in a string list.

    If the file doesn't exist or isn't readable, return an empty list.
    Also strip all comments, if any.
    """

    if not os.path.isfile(path):
        return []

    try:
        f = open(path, 'r')
        contents = f.read()
        f.close()
        return shlex.split(contents, True)
    except:
        return []


def read_vars_file(path):
    """Return a dictionary read from a shell vars file.
    """
    
    contents = read_config_file(path)
    try:
        # TODO: maybe return at least all the valid pairs?
        return dict(v.split('=') for v in contents)
    except:
        return {}


def localized_names(lang):
    """Return a dictionary with the translations of XDG directories for lang.
    """

    # If lang is unset, the current locale is used
    if lang:
        oldlang = os.environ['LANG']
        os.environ['LANG'] = lang

    # Directory names are from xdg-user-dirs/translate.c
    result = {
        'Applications': T_('Applications'),
        'Desktop': T_('Desktop'),
        'Documents': T_('Documents'),
        'Download': T_('Download'),
        'Downloads': T_('Downloads'),
        'Movies': T_('Movies'),
        'Music': T_('Music'),
        'Photos': T_('Photos'),
        'Pictures': T_('Pictures'),
        'Projects': T_('Projects'),
        'Public': T_('Public'),
        'Share': T_('Share'),
        'Templates': T_('Templates'),
        'Videos': T_('Videos')
        }

    if lang:
        os.environ['LANG'] = oldlang

    return result


def localize_dir(path, lnames):
    """Localize a default XDG dir like e.g. Documents/Pictures.
    """

    components = path.split('/')
    for i in range(len(components)):
        if components[i] in lnames:
            components[i] = lnames[components[i]]

    return '/'.join(components)


def default_dirs(lang):
    """Return the default XDG dirs for lang.

    These are read from /etc/xdg/user-dirs.defaults.
    """

    # Map from default xdg dirs to normal lowercase vars
    d2n = {
        'APPLICATIONS': 'Applications',
        'DESKTOP': 'Desktop',
        'DOCUMENTS': 'Documents',
        'DOWNLOAD': 'Download',
        'DOWNLOADS': 'Downloads',
        'MOVIES': 'Movies',
        'MUSIC': 'Music',
        'PHOTOS': 'Photos',
        'PICTURES': 'Pictures',
        'PROJECTS': 'Projects',
        'PUBLIC': 'Public',
        'PUBLICSHARE': 'Public',
        'SHARE': 'Share',
        'TEMPLATES': 'Templates',
        'VIDEOS': 'Videos'}

    lnames = localized_names(lang)
    ddirs = read_vars_file('/etc/xdg/user-dirs.defaults')
    result = lnames
    for key, val in ddirs.iteritems():
        if key in d2n:
            result[d2n[key]] = localize_dir(val, lnames)

    return result


def user_dirs(home):
    """Return the user XDG dirs for the user at "home".

    These are read from ~/.config/user-dirs.dirs.
    """

    # Map from user xdg dirs to normal lowercase vars
    u2n = {
        'XDG_APPLICATIONS_DIR': 'Applications',
        'XDG_DESKTOP_DIR': 'Desktop',
        'XDG_DOCUMENTS_DIR': 'Documents',
        'XDG_DOWNLOAD_DIR': 'Download',
        'XDG_DOWNLOADS_DIR': 'Downloads',
        'XDG_MOVIES_DIR': 'Movies',
        'XDG_MUSIC_DIR': 'Music',
        'XDG_PHOTOS_DIR': 'Photos',
        'XDG_PICTURES_DIR': 'Pictures',
        'XDG_PROJECTS_DIR': 'Projects',
        'XDG_PUBLIC_DIR': 'Public',
        'XDG_PUBLICSHARE_DIR': 'Public',
        'XDG_SHARE_DIR': 'Share',
        'XDG_TEMPLATES_DIR': 'Templates',
        'XDG_VIDEOS_DIR': 'Videos'}

    udirs = read_vars_file("%s/.config/user-dirs.dirs" % home)
    result = {}
    for key, val in udirs.iteritems():
        if key in u2n:
            result[u2n[key]] = val

    return result


def user_lang(home):
    """Return the user language for XDG directories, if set.
    """

    contents = read_config_file("%s/.config/user-dirs.locale" % home)
    if len(contents) == 1:
        return contents[0]
    else:
        return ''
    

def system_lang():
    """Return the default system locale which is applied to new users.
        
    It is read from /etc/default/locale.
    """

    flocale = read_vars_file('/etc/default/locale')
    return flocale.get('LANG', '')


def expand_home(dic, home):
    """
    """
#    for key in result.keys():
#        if result[key].startswith('$HOME'):
#            result[key] = result[key].replace('$HOME', home)
#
#    dict.get(key, default) will be useful
#    key in dict also
#    pop(key, default)
#    setdefault(key, default)
#    update(other_dict)
#    dict | other → union
    pass

    
def get_xdg_dirs(user):
    """Return a dictionary with the xdg dirs for that user.

    If any or all of that user's xdg dirs aren't set, return the default
    xdg dirs based on the default system locale.
    Raise an error if the user doesn't exist.
    """

    # The caller is responsible to catch any exceptions raised by these:
    if type(user) is int:
        pwentry = pwd.getpwuid(user)
    else:
        pwentry = pwd.getpwnam(user)

    # Do a basic check that no system user was selected
    if pwentry.pw_uid < 999:
        raise Exception('Tried to get the xdg dirs for a system user')    

    home = pwentry.pw_dir
    
    # If a ~/.config/user-dirs.locale exists, use it
    lang = user_lang(home)

    # Otherwise use the default system language, or '' for the current lang
    if not lang:
        lang = system_lang()

    # Get the default and the user specified directories
    ddirs = default_dirs(lang)
    udirs = user_dirs(home)

    # And merge them into result, while replacing $HOME when necessary
    result = ddirs
    result.update(udirs)
    for key, val in result.iteritems():
        if val.startswith('$HOME'):
            result[key] = val.replace('$HOME', home, 1)
        elif not val.startswith('/'):
            result[key] = home + '/' + val

    return result


# Allow xdg_dirs to be ran from the command line
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        user = sys.argv[1]
    else:
        user = os.environ["USER"]

    for key, val in get_xdg_dirs(user).iteritems():
        print "%s=%s" % (key, val)
