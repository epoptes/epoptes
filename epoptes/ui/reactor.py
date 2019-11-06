# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
A small workaround to avoid many pylint3 import-related warnings.
"""
import epoptes.ui.common
from twisted.internet import gtk3reactor
# This must be run after epoptes.ui.common (=Gtk imported without version)
# and before twisted.internet.reactor (=reactor already installed)
gtk3reactor.install()
from twisted.internet import reactor
