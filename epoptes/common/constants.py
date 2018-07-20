# This file is part of Epoptes, http://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Common constants.
"""

# Warn users to update their clients if they have a lower version than this:
COMPATIBILITY_VERSION = '0.5'

# ['ltsp123', '00-1b-24-89-65-d6', '127.0.0.1:46827', '10.160.31.126:44920',
#  'thin', 'user3', <gtk.gdk.Pixbuf>, '10.160.31.123', 'user (ltsp123)']
C_LABEL = 0
C_PIXBUF = 1
C_INSTANCE = 2
C_SESSION_HANDLE = 3
# [label, <gtk.gdk.Pixbuf>, <Client instance>, username]
G_LABEL = 0
G_INSTANCE = 1

# Execution Modes are used in execOnClients
EM_SESSION_ONLY = 0
EM_SYSTEM_ONLY = 1
EM_EXIT_IF_SENT = 2
EM_SESSION = [EM_SESSION_ONLY]
EM_SESSION_AND_SYSTEM = [EM_SESSION_ONLY, EM_SYSTEM_ONLY]
EM_SESSION_OR_SYSTEM = [EM_SESSION_ONLY, EM_EXIT_IF_SENT, EM_SYSTEM_ONLY]
EM_SYSTEM_OR_SESSION = [EM_SYSTEM_ONLY, EM_EXIT_IF_SENT, EM_SESSION_ONLY]
EM_SYSTEM_AND_SESSION = [EM_SYSTEM_ONLY, EM_SESSION_ONLY]
EM_SYSTEM = [EM_SYSTEM_ONLY]
