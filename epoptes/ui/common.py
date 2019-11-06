# This file is part of Epoptes, https://epoptes.org
# Copyright 2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Define required gi package versions in a common place, and install gettext.

Rationale:
gi requires something like:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
This conflicts with https://www.python.org/dev/peps/pep-0008/#imports
and triggers pycodestyle's "E402 module level import not at top of file".
The following is a bit better:
    import sys  # Import standard library modules

    import twisted  # Import third party modules

    from epoptes.ui.common import gettext as _  # Import local modules
    from gi.repository import Gtk, Gdk
That last line "only" triggers pylint's "wrong-import-position" once.
"""
import errno
import gettext
import locale
import os

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Notify', '0.7')
gettext.textdomain('epoptes')
locale.textdomain('epoptes')
gettext = gettext.gettext


def locate_resource(filename, absolute=True):
    """Search for filename in some known paths."""
    # Use recursion for absolute instead of multiple ifs:
    if absolute:
        return os.path.abspath(locate_resource(filename, False))
    test = filename
    if os.path.isfile(test):
        return test
    test = "/usr/share/epoptes/" + os.path.basename(filename)
    if os.path.isfile(test):
        return test
    test = "/usr/share/epoptes/images/" + os.path.basename(filename)
    if os.path.isfile(test):
        return test
    raise FileNotFoundError(
        errno.ENOENT, os.strerror(errno.ENOENT), filename)
