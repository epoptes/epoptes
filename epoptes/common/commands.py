#-*- coding: utf-8 -*-
import os


class commands:
    """
    Define here all epoptes custom commands
    """

    def __init__(self):

        self.POWEROFF = './endsession --shutdown '
        self.REBOOT = './endsession --reboot '
        self.LOGOUT = './endsession --logout '
        self.EXEC = './execute '

        self.SCREENSHOT = 'if ./screenshot %i %i; \
                then BAD_SCREENSHOTS=0; elif [ "$BAD_SCREENSHOTS" = 3 ]; \
                then exit 1; else BAD_SCREENSHOTS=$(($BAD_SCREENSHOTS+1)); fi'

        self.EXEC_AMIXER = './execute amixer -c 0 -q sset Master '

        self.POWEROFF_WARN = _('Are you sure you want to shutdown all the computers?')
        self.REBOOT_WARN = _('Are you sure you want to reboot all the computers?')
        self.LOGOUT_WARN = _('Are you sure you want to log off all the users?')
        self.KILLALL_WARN = _('Are you sure you want to terminate all processes of the selected users?')

    def __setattr__(self, cmd, val):
        """
        Set new constants and prevent from changing values from already
        set constants
        """

        if hasattr(self, cmd):
            raise ValueError, 'Command %s is already set' % cmd

        self.__dict__[cmd] = val
