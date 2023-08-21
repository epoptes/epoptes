#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2023 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
This setup script needs python-distutils-extra, an extension to the standard
distutils which provides i18n, icon support, etc.
https://launchpad.net/python-distutils-extra
"""
import glob
import posixpath
import re

import DistUtilsExtra.auto


def changelog_version(changelog="debian/changelog"):
    """Parse the version from debian/changelog."""
    version = "1.0.dev0"
    if not posixpath.exists(changelog):
        return version
    with open(changelog, encoding="utf-8") as file:
        head = file.readline()
    match = re.compile(r".*\((.*)\).*").match(head)
    if not match:
        return version
    version = match.group(1)
    # Mangle the version until LP #2032185 is resolved
    version = version.replace("+", "~").replace("~", "+", 1).replace("~", "-")
    return version


def subtract_files(set1, set2):
    """Return the set of files 'set1-set2'."""
    result = set(set1)
    for _dir, files in set2:
        result -= set(files)
    return list(result)


def main():
    """Run `setup.py --help` for usage."""
    client_special_files = [
        ('/etc/xdg/autostart/',
         ['epoptes-client/epoptes-client.desktop']),
        ('/usr/sbin/',
         ['epoptes-client/epoptes-client'])]
    client_usr_share_files = [
        ('/usr/share/epoptes-client/',
         subtract_files(glob.glob('epoptes-client/*'), client_special_files))]
    server_special_files = [
        ('/usr/share/ltsp/plugins/ltsp-build-client/common/',
         ['data/040-epoptes-certificate'])]

    DistUtilsExtra.auto.setup(
        name='epoptes',
        version=changelog_version(),
        description='Computer lab administration and monitoring tool',
        url='https://epoptes.org',
        license='GNU GPL v3',
        author='Fotis Tsamis',
        author_email='ftsamis@gmail.com',
        requires='',
        py_modules=['twisted.plugins.epoptesd'],
        data_files=client_special_files + client_usr_share_files +
        server_special_files)


if __name__ == '__main__':
    main()
