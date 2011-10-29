#!/usr/bin/env python
# -*- coding: utf-8 -*-

###########################################################################
# This script needs python-distutils-extra, an extension to the standard
# distutils which provides i18n, icon support, etc.
# https://launchpad.net/python-distutils-extra
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

from glob import glob
from distutils.version import StrictVersion

try:
    import DistUtilsExtra.auto
except ImportError:
    import sys
    print >> sys.stderr, 'To build epoptes you need https://launchpad.net/python-distutils-extra'
    sys.exit(1)

assert StrictVersion(DistUtilsExtra.auto.__version__) >= '2.4', 'needs DistUtilsExtra.auto >= 2.4'

import posixpath, re

def changelog_version(changelog="debian/changelog"):
    version = "dev"
    if posixpath.exists(changelog):
        head=open(changelog).readline()
        match = re.compile(".*\((.*)\).*").match(head)
        if match:
            version = match.group(1)

    return version

DistUtilsExtra.auto.setup(
    name='epoptes',
    version = changelog_version(),
    description = 'Computer lab administration and monitoring tool',
    url = 'https://launchpad.net/epoptes',
    license = 'GNU GPL v3',
    author = 'Fotis Tsamis',
    author_email = 'ftsamis@gmail.com',
    py_modules = ['twisted.plugins.epoptesd'],
)
