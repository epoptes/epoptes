#!/usr/bin/env python

# Copyright (C) 2011 Alkis Georgopoulos

# This script needs python-distutils-extra, an extension to the standard
# distutils which provides i18n, icon support, etc.
# https://launchpad.net/python-distutils-extra

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
