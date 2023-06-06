# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2023 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Configuration file parser and other default configuration variables.
TODO: change settings into a class.
"""
import configparser
import glob
import json
import os
import shlex

from epoptes.common.constants import G_INSTANCE
from epoptes.core import logger, structs
from epoptes.ui.common import gettext as _


LOG = logger.Logger(__file__)


def expand_filename(filename):
    """Return the full path for the specified user settings file."""
    return os.path.join(os.path.expanduser('~/.config/epoptes/'), filename)


def makedirs_for_file(filename):
    """Ensure that the directory where filename resides, exists."""
    dirname = os.path.dirname(filename)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def read_plain_file(filename):
    """Return the whole contents of a plain text file into a string list.
    If the file doesn't exist or isn't readable, return an empty list.
    """
    if not os.path.isfile(filename):
        return []
    try:
        with open(filename, 'r') as file:
            contents = [x.strip() for x in file.readlines()]
        return contents
    except (IOError, OSError) as exc:
        LOG.e(exc)
        return []


def write_plain_file(filename, contents):
    """Write the contents string list to filename. Return True on success."""
    try:
        makedirs_for_file(filename)
        with open(filename, 'w') as file:
            file.write('\n'.join(contents))
        return True
    except (IOError, OSError) as exc:
        LOG.e(exc)
        return False


def read_ini_file(filename):
    """Return a ConfigParser from the contents of a configuration file."""
    conf = configparser.ConfigParser()
    try:
        conf.read(filename)
    except (IOError, OSError) as exc:
        LOG.e(exc)
    return conf


def write_ini_file(filename, contents):
    """Write contents to a ConfigParser file. Return True on success."""
    try:
        makedirs_for_file(filename)
        with open(filename, 'w') as file:
            contents.write(file)
        return True
    except (IOError, OSError) as exc:
        LOG.e(exc)
        return False


def read_shell_file(filename):
    """Return the variables of a shell-like configuration file in a dict.
    If the file doesn't exist or isn't readable, return an empty list.
    Also strip all comments, if any.
    """
    if not os.path.isfile(filename):
        return {}
    try:
        with open(filename, 'r') as file:
            contents = file.read()
        contents = shlex.split(contents, True)
        # TODO: maybe return at least all the valid pairs?
        return dict(v.split('=') for v in contents)
    except (IOError, OSError) as exc:
        LOG.e(exc)
        return {}


def read_groups(filename):
    """Parse a JSON file and create the appropriate group and client objects.
    Return a 2-tuple with a client instances list and a group instances list.
    """
    if not os.path.isfile(filename):
        return [], []
    try:
        with open(filename) as file:
            data = json.loads(file.read())
    except (IOError, OSError) as exc:
        LOG.e(exc)
        return [], []

    saved_clients = {}

    for key, cln in data['clients'].items():
        new = structs.Client('offline', cln['mac'], '', cln['alias'])
        saved_clients[key] = new

    groups = []
    for group in data['groups']:
        members = {}
        for key, dct in group['members'].items():
            members[saved_clients[key]] = dct

        groups.append(structs.Group(group['name'], members))

    return saved_clients.values(), groups


def save_groups(filename, model):
    """Save the groups and their members from model (gtk.ListStore) in JSON
    format.
    """
    data = {'clients': {}, 'groups': []}
    uid = 0
    uid_pairs = {}
    saved_clients = []

    # Create a list with all the clients we want to save
    for group in model:
        group = group[G_INSTANCE]
        for cln in group.get_members():
            if cln not in saved_clients:
                saved_clients.append(cln)

    for cln in saved_clients:
        # Use an integer ID as a key instead of the memory address
        data['clients'][uid] = {'mac': cln.mac, 'alias': cln.alias}
        # Pair memory addresses with integer IDs
        uid_pairs[cln] = uid
        uid += 1

    for group in model:
        group = group[G_INSTANCE]
        members = {}
        # Get the IDs created above
        for cln, props in group.members.items():
            members[uid_pairs[cln]] = props
        data['groups'].append({'name': group.name, 'members': members})

    # Save the dict in JSON format
    try:
        makedirs_for_file(filename)
        with open(filename, 'w') as file:
            file.write(json.dumps(data, indent=2))
    except (IOError, OSError) as exc:
        LOG.e(exc)


system = {}
# The system settings are shared with epoptes-client, that's why the caps.
for fname in glob.glob('/etc/default/epoptes') + \
        glob.glob('/etc/epoptes/common/*.conf') + \
        glob.glob('/etc/epoptes/server/*.conf'):
    system.update(read_shell_file(fname))
# TODO: check if the types, e.g. PORT=int, may cause problems.
system.setdefault('PORT', 789)
system.setdefault('SOCKET_GROUP', 'epoptes')
system.setdefault('DIR', '/run/epoptes')
system.setdefault('THUMBSHOT_MS', 5000)
# The epoptes SERVER key is used for SSH socket forwarding
system.setdefault('SERVER', 'server')
# Allow running unencrypted, for clients with very low RAM.
try:
    if os.path.getsize('/etc/epoptes/server.crt') == 0:
        system.setdefault('ENCRYPTION', False)
except (IOError, OSError) as ex:
    LOG.e(ex)
finally:
    system.setdefault('ENCRYPTION', True)

settings = read_ini_file(expand_filename('settings'))
if not settings.has_section('GUI'):
    settings.add_section('GUI')
if not settings.has_option('GUI', 'messages_default_title'):
    settings.set('GUI', 'messages_default_title',
                 _('Message from administrator'))
if not settings.has_option('GUI', 'messages_use_markup'):
    settings.set('GUI', 'messages_use_markup', 'False')
if not settings.has_option('GUI', 'grabkbdptr'):
    settings.set('GUI', 'grabkbdptr', 'False')

history = read_plain_file(expand_filename('history'))
