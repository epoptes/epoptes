#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
# Message sending.
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

from . import gi_versions
from gi.repository import Gtk
import os

from ..common import config


def startSendMessageDlg(parent):
    """
    Retrieve dialog window from glade format and
    according to type of message requested to send
    Returns: a 2-tuple containing the message text
    and the message type.
    """

    wTree = Gtk.Builder()
    get = lambda obj: wTree.get_object(obj)
    wTree.add_from_file('sendMessage.ui')
    dlg = get('sendMessageDialog')
    dlg.set_transient_for(parent)

    textView = get('Message')
    title_entry = get('title_entry')
    title_entry.set_text(config.settings.get('GUI', 'messages_default_title'))
    use_markup_toggle = get('use_markup_toggle')
    use_markup_toggle.set_active(config.settings.getboolean('GUI', 'messages_use_markup'))

    reply = dlg.run()
    msg = ()

    if reply == 1:
        buf = textView.get_buffer()
        s = buf.get_start_iter()
        e = buf.get_end_iter()
        text = textView.get_buffer().get_text(s, e, False)

        title = title_entry.get_text().strip()

        use_markup = use_markup_toggle.get_active()

        msg = (text, title, use_markup)

        config.settings.set('GUI', 'messages_default_title', title)
        config.settings.set('GUI', 'messages_use_markup', str(use_markup))

        f = open(os.path.expanduser('~/.config/epoptes/settings'), 'w')
        config.settings.write(f)
        f.close()
    # Hide dialog after any kind of function
    dlg.hide()

    # Return the command to be executed on clients
    return msg
