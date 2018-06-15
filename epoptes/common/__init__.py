# This file is part of Epoptes, http://epoptes.org
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

    from epoptes.common import gettext as _  # Import local modules
    from gi.repository import Gtk, Gdk
That last line "only" triggers pylint's "wrong-import-position" once.
"""
import gettext
import locale

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Notify', '0.7')
gettext.textdomain('epoptes')
locale.textdomain('epoptes')
gettext = gettext.gettext
