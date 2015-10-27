#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# Classes for creating client and group objects.
#
# Copyright (C) 2011 Fotis Tsamis <ftsamis@gmail.com>
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

clients = []
class Client:
    def __init__(self, type='', mac='', hostname='', alias='', users={}, hsystem=''):
        self.type = type
        self.mac = mac.upper()
        self.hostname = hostname
        self.alias = alias
        self.users = users.copy()
        self.hsystem = hsystem
        clients.append(self)
    
    def set_offline(self):
        self.hsystem = ''
        self.users = {}
        self.type = 'offline'
        self.hostname = ''
    
    def is_offline(self):
        """Return True only if there is no system or session handle
        for this client but there is a MAC address.
        """
        return not(self.users or self.hsystem) and self.mac
        
    def get_name(self):
        """Return the alias of the client or the hostname if the 
        alias is not set, or if both are unset (offline clients)
        return the MAC address.
        """
        return self.alias or self.hostname or self.mac
        
    def set_name(self, name):
        self.alias = name
        
    def add_user(self, username, realname, handle):
        self.users[handle] = {'uname' : username, 'rname' : realname}


class Group:
    def __init__(self, name="New group", members={}):
        self.name = name
        #{<instance> : {'x_pos':342, 'y_pos':112, 'size':600}}
        self.members = members.copy()
    
    def get_members(self):
        """Return a list with all the clients that are members of the group"""
        return self.members.keys()
    
    def has_client(self, client):
        """Check if a client is member of the group"""
        return client in self.members
    
    def add_client(self, client, **props):
        """Add a client to the group"""
        self.members[client] = {}
        self.set_properties(client, **props)
    
    def remove_client(self, client):
        """Remove a client from the group"""
        del self.members[client]
    
    def set_properties(self, client, **props):
        """Set x_pos, y_pos or size property for a client on the group"""
        for prop, value in props.iteritems():
            if isinstance(value, (int, float)):
                self.members[client][prop] = value
                #TODO: Save the new values to the disk.
            else:
                raise TypeError("The value of '%s' must be a number." % prop)
                
    def get_property(self, client, prop):
        """Return the value of the 'prop' property for client"""
        return self.members[client][prop]
    
