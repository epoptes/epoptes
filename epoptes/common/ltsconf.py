#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# This will read lts.conf and enumerate the clients by MAC so they
# can be started up with Wake-On-Lan.
#
# Copyright (C) 2010 Fotis Tsamis <ftsamis@gmail.com>
# 2018, Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL".
###########################################################################

import re
import os


class ltsConf:
    
    def __init__(self):
        self.rmcomment = lambda string: string.split('#')[0].strip()
        self.getvar = lambda string: self.rmcomment(string).split('=', 1)[0].strip()
        self.getval = lambda string: self.rmcomment(string).split('=', 1)[1].strip()
        self.filename = '/var/lib/tftpboot/ltsp/i386/lts.conf'
        self.parse()
        
    def parse(self):
        if os.path.isfile(self.filename):
            file = open(self.filename)
            lines = file.readlines()
            file.close()
        else:
            lines = []
        
        self.content = lines#''.join(lines)
        self.clients = {}
        
        cursection = None
        for i in range(len(lines)):
            curline = lines[i].strip()
            
            if curline == '':
                continue
            
            elif curline[0] == '[':
                if re.match('\[..:..:..:..:..:..\]', curline):
                    cursection = self.rmcomment(curline).strip('[]').upper()
                    self.clients[cursection] = {}
                else:
                    cursection = None
            
            elif '=' in self.rmcomment(curline) and cursection != None:
                item = self.getvar(curline)
                value = self.getval(curline)
                self.clients[cursection][item] = value
    
    def write(self):
        data = self.content#.strip().readlines()
        f = open(self.filename,'w')#'/var/lib/tftpboot/ltsp/i386/lts.conf', 'w')
        
        cursection = None
        for i in range(len(data)):
            curline = data[i].strip()
            
            if curline == '':
                f.write('\n')
            
            elif curline[0] == '[':
                cursection = self.rmcomment(curline).strip('[]')
                if re.match('\[..:..:..:..:..:..\]', curline):
                    if cursection in self.clients:
                        f.write(data[i])
                    else:
                        cursection = None
                else:
                    cursection = 'ignored'
                    f.write(data[i])
            
            elif curline[0] == '#':
                f.write(data[i])
            
            elif '=' in self.rmcomment(curline) and cursection != None:
                if cursection == 'ignored':
                    f.write(data[i])
                elif self.getvar(curline) in self.clients[cursection]:
                    dat = data[i].replace(self.getval(curline), self.clients[cursection][self.getvar(curline)])
                    f.write(dat)
        
        f.close()
        self.parse()
    
    def getSavedClients(self):
        list = []
        for client, vars in self.clients.items():
            if 'HOSTNAME' in vars:
                list.append(client)
        return list
    
    def isSaved(self, mac):
        if mac in self.getSavedClients():
            return True
        return False
        
    def saveClient(self, mac, hostname):
        if self.isSaved(mac):
            return
        #FIXME: section may exists
        f = open(self.filename, 'a')
        f.write('\n[%s]\n\tHOSTNAME=%s\n' %(mac, hostname))
        f.close()
        self.parse()
    
    def removeClient(self, mac):
        if isSaved(mac):
            del self.clients[mac]['HOSTNAME']
            self.write()
        
    def set(self, section, item, value):
        self.clients[section][item] = value
        self.write()
    
    def getHostname(self, mac):
        if self.isSaved(section):
            return self.clients[section]['HOSTNAME']
    
    
    # DELETE US
    def getItem(self, section, item):
        if self.itemExists(section, item):
            return self.clients[section][item]
        
    def addItem(self, section, item, value):
        pass
    
    def rmSection(self, name):
        if sectionExists(name):
            del self.clients[name]
            self.write()
    
    def getSections(self):
        return list(self.clients.keys())
    
    def sectionExists(self, section):
        if section in self.clients:
            return True
        return False
    
    def itemExists(self, section, item):
        if self.sectionExists(section) and item in self.clients[section]:
            return True
        return False
