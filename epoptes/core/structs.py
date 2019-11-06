# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Classes for creating client and group objects.
"""
clients = []


class Client:
    """An epoptes client."""
    def __init__(self, type_='', mac='', hostname='', alias='', users=None,
                 hsystem=''):
        self.type = type_
        self.mac = mac.lower()
        self.hostname = hostname
        self.alias = alias
        if users is None:
            self.users = {}
        else:
            self.users = users.copy()
        self.hsystem = hsystem
        clients.append(self)

    def set_offline(self):
        """Indicate that a client is now offline."""
        self.hsystem = ''
        self.users = {}
        self.type = 'offline'
        self.hostname = ''

    def is_offline(self):
        """Return True only if there is no system or session handle for this
        client but there is a MAC address.
        """
        return not(self.users or self.hsystem) and self.mac

    def get_name(self):
        """Return the alias of the client or the hostname if the alias is not
        set, or if both are unset (offline clients) return the MAC address.
        """
        return self.alias or self.hostname or self.mac

    def set_name(self, name):
        """Set the client alias."""
        self.alias = name

    def add_user(self, username, realname, handle):
        """Add a user in the users dict."""
        self.users[handle] = {'uname': username, 'rname': realname}


class Group:
    """A group of epoptes clients."""
    def __init__(self, name, members):
        self.name = name
        # {<instance> : {'x_pos':342, 'y_pos':112, 'size':600}}
        self.members = members.copy()

    def get_members(self):
        """Return a list with all the clients that are members of the group."""
        return self.members.keys()

    def has_client(self, client):
        """Check if a client is member of the group."""
        return client in self.members

    def add_client(self, client, **props):
        """Add a client to the group."""
        self.members[client] = {}
        self.set_properties(client, **props)

    def remove_client(self, client):
        """Remove a client from the group."""
        del self.members[client]

    def set_properties(self, client, **props):
        """Set x_pos, y_pos or size property for a client on the group."""
        for prop, value in props.items():
            if isinstance(value, (int, float)):
                self.members[client][prop] = value
                # TODO: Save the new values to the disk.
            else:
                raise TypeError("The value of '%s' must be a number." % prop)

    def get_property(self, client, prop):
        """Return the value of the 'prop' property for client."""
        return self.members[client][prop]
