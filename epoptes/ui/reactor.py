# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
A small workaround to avoid many pylint3 import-related warnings,
and a proper "on_stop" hook for reactor.
"""
import epoptes.ui.common
from twisted.internet import gireactor


class Gtk3Reactor(gireactor.GIReactor):
    """
    A reactor using the gtk3+ event loop.
    Copied from gtk3reactor in order to provide a proper "on_stop" hook.
    """

    def __init__(self):
        """
        Override init to set the C{useGtk} flag.
        """
        gireactor.GIReactor.__init__(self, useGtk=True)
        self.on_stop = None

    def stop(self) -> None:
        """
        See twisted.internet.interfaces.IReactorCore.stop.
        """
        if self.on_stop:
            self.on_stop()
        super().stop()


# These must be run after epoptes.ui.common (=Gtk imported without version)
# and before twisted.internet.reactor (=reactor already installed)
reactor = Gtk3Reactor()
from twisted.internet.main import installReactor
installReactor(reactor)

from twisted.internet import reactor
