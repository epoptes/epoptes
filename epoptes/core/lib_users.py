#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# Imports/exports user accounts from/to various sources.
#
# Copyright (C) 2009-2018 Alkis Georgopoulos <alkisg@gmail.com>
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

import pwd
import spwd
import grp
import operator
import csv
import subprocess
import re
import crypt
import random

# I split pw_gecos to rname, office, wphone, hphone
# I also use an additional field called plainpw, for plain text passwords.


DEFAULT_GROUPS = ["cdrom", "floppy", "dialout", "tape", "dip", "adm", "plugdev",
    "fax", "fuse", "video"]
FIELD_NAMES = ["Όνομα χρήστη", "UID", "Ονοματεπώνυμο", "Γραφείο", 
    "Τηλ. εργασίας", "Τηλ. οικίας", "Προσωπικός φάκελος", "Κέλυφος", "Ομάδες",
    "Ελάχιστη διάρκεια κωδικού", "Μέγιστη διάρκεια κωδικού", 
    "Ημέρες προειδοποίησης λήξης", "Ημέρες απενεργοποίησης μετά τη λήξη",
    "Ημέρες κλειδωμένου κωδικού", "Κρυπτογραφημένος κωδικός", 
    "Κωδικός πρόσβασης"]

UID_MIN = 1000  # TODO: the callee should read them from /etc/adduser.conf
UID_MAX = 60000 # and pass them to the command line.

class User:
    def __init__(self, name, uid='', rname='', office='', wphone='',
                 hphone='', dir='', shell='', groups=[], min='', max='',
                 warn='', inact='', expire='', pwd='', plainpw=''):

        self.name, self.uid, self.rname, self.office, self.wphone, self.hphone,\
        self.dir, self.shell, self.groups, self.min, self.max, self.warn, \
        self.inact, self.expire, self.pwd, self.plainpw = name, uid, rname, \
        office, wphone, hphone, dir, shell, groups, min, max, warn, inact, \
        expire, pwd, plainpw

def run_command(cmdline):
    # Runs a command and returns either an empty string, on successful
    # completion, or the whole stdout and stderr of the command, on error.

    # Popen doesn't like integers like uid or gid in the command line.
    cmdline = [str(s) for s in cmdline]

    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = p.wait()
    if res == 0:
        return ""
    else:
        print("Σφάλμα κατά την εκτέλεση εντολής:")
        print(" $ %s" % ' '.join(cmdline))
        print(p.stdout.read())
        err = p.stderr.read()
        print(err)
        if err == '':
            err = "\n"
        return err


def sorted_users(users):
    # TODO
    return users


def read_users_from_passwd(dirname="/etc"):
    """
    Reads users from /etc/passwd, /etc/shadow (if it has access) and /etc/group
    """
    pwds = pwd.getpwall()
    spwds = spwd.getspall()
    sn = {}
    for s in spwds:
        sn[s.sp_nam] = s
    users = {}

    for p in pwds:
        if p.pw_uid >= UID_MIN and p.pw_uid <= UID_MAX:
            if p.pw_name in sn:
                s = sn[p.pw_name]
            else:
                # print(" * I couldn't find user %s in shadow file. Are you \
#root?" % p.pw_name)
                s = spwd.struct_spwd(["", "x", "", "", "", "", "", "", ""])
            rname, office, wphone, hphone = (p.pw_gecos + ",,,").split(",")[:4]
            u = User(p.pw_name, p.pw_uid, rname, office, wphone, hphone,
                p.pw_dir, p.pw_shell, [], s.sp_min, s.sp_max, s.sp_warn, 
                s.sp_inact, s.sp_expire, s.sp_pwd, "")
            if u.inact == -1:
                u.inact = ''
            if u.expire == -1:
                u.expire = ''
            users[u.name] = u

    grps = grp.getgrall()
    for g in grps:
        for gu in g.gr_mem:
            if gu in users:
                users[gu].groups.append(g.gr_name)

    return sorted_users(users)


def print_user(u):
    """
    Prints a user to stdout, mainly for debugging
    """
    print(u.name, u.uid, u.rname, u.office, u.wphone, u.hphone, u.dir, u.shell,\
        u.groups, u.min, u.max, u.warn, u.inact, u.expire, u.pwd, u.plainpw)


def print_users(users):
    """
    Prints all the users to stdout, mainly for debugging
    """
    for name, u in users.items():
        print_user(u)


def export_users_to_csv(users, filename):
    """
    Exports users to a comma-seperated-values file
    """
    cw = csv.writer(open(filename, "w"))
    cw.writerow(FIELD_NAMES)
    for name, u in users.items():
        cw.writerow([u.name, u.uid, u.rname, u.office, u.wphone, u.hphone, 
            u.dir, u.shell, ",".join(u.groups), u.min, u.max, u.warn, u.inact, 
            u.expire, u.pwd, u.plainpw])


def import_users_from_csv(filename):
    """
    Imports users from a comma-seperated-values file
    """
    cr = csv.reader(open(filename, "r"))
    if next(cr) != FIELD_NAMES:
        print("Wrong headers in .csv file. Please use an exported file as a \
            template, and don't change the headers or move columns.")
        return {}

    users={}
    for row in cr:
        u=User(*row)
        u.groups = u.groups.split(',')
        users[u.name]=u

    return users


def import_users_from_sch(clipboard):
    """
    Imports users from the register.sch.gr/studentsadmin web page.
    """
    header = "A.A\tΕνεργός\tΌνομα Χρήστη\tΕπώνυμο\tΌνομα\tΚηδεμόνας\tΑρ. \
        Μητρώου\tΤμήμα\tΤύπος Λογαριασμού"

    clipboard = re.sub(" *\t *", "\t", clipboard)
    second_line = clipboard.split("\n",3)[1:2]

    if second_line != [header]:
        print("Unexpected header line:", "\n".join(second_line))
        return {}
    usersdata = re.findall('([0-9 ]*)\t\t(.*)\t(.*)\t(.*)\t(.*)\t(.*)\t(.*)\t(.*)', 
        clipboard)

    users = {}
    for user in usersdata:
        u = User(name=user[1].strip(), rname=user[2].strip() + ' ' + 
                user[3].strip(), office=user[4].strip(), 
                groups=[user[6].strip(), user[7].strip()] + DEFAULT_GROUPS,
                plainpw=user[1].strip())
        users[u.name] = u

    return users
    

def mkpasswd(plainpw):
    """
    Converts a plain text password to a sha-512 encrypted one.
    """
    alphabet='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    salt=''.join([ random.choice(alphabet) for i in range(8) ])

    return crypt.crypt(plainpw, "$6$%s$" % salt)


def add_group(gname, gid=""):
    """
    Adds a group to /etc/group.
    Returns "" on success or the output if addgroup failed.
    """
    # It's not an error if the group already exists
    grps = grp.getgrall()
    for g in grps:
        if g.gr_name == gname:
            return ""

    cmdline = ["addgroup", gname]
    if gid != "":
        cmdline.extend(["--gid", gid])

    return run_command(cmdline)


def add_user(u):
    """
    Adds a user to /etc/passwd.
    Returns "" on success or the output if any error occurred
    """
    cmdline = ["useradd", "--create-home", "--user-group"]

    if u.name == "":
        print("add_user: missing name")
        return False

    if u.uid != "":
        cmdline.extend(["--uid", u.uid])

    gecos = ','.join([u.rname, u.office, u.wphone, u.hphone])
    cmdline.extend(["--comment", gecos])

    if u.dir != "":
        cmdline.extend(["--home", u.dir])

    if u.shell != "":
        shell = u.shell
    else:
        shell = "/bin/bash"
    cmdline.extend(["--shell", shell])

    if u.min != "":
        cmdline.extend(["--key", "PASS_MIN_DAYS=%s" % u.min])

    if u.max != "":
        cmdline.extend(["--key", "PASS_MAX_DAYS=%s" % u.max])

    if u.warn != "":
        cmdline.extend(["--key", "PASS_WARN_AGE=%s" % u.warn])

    if u.inact != "":
        cmdline.extend(["--inactive", u.inact])

    if u.expire != "":
        cmdline.extend(["--expiredate", u.expire])

    # TODO: create the groups before using them
    groups = ','.join(u.groups)
    if groups == "":
        groups = ','.join(DEFAULT_GROUPS)
    cmdline.extend(["--groups", groups])

    if u.plainpw != "":
        pwd = mkpasswd(u.plainpw)
    else:
        pwd = u.pwd
    if pwd != "":
        cmdline.extend(["--password", pwd])

    cmdline.append(u.name)

    return run_command(cmdline)


def write_users_to_passwd(users, dirname="/etc"):
    for name, u in users.items():
        add_user(u)


def print_bold(message):
    print("\033[;;1m%s\033[;;m" % message)
