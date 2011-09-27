#-*- coding: utf-8 -*-
class Constants:
    """
    Define here all constants 
    """
    
    ZENITY_INFO = 'zenity --info '
    ZENITY_WARNING = 'zenity --warning '
    ZENITY_ERROR = 'zenity --error '

    HOME_DIR = '/home/'
    HOME_PREFIX = '~/'
    XDG_DOCUMENTS_DIR = 'Documents'
    GROUP_PAT = '{g}'
    MAX_DIRS = 50

    MODE_R = 0744
    MODE_W = 0733
    MODE_RW = 0766

    EXISTS_STR = "Ναι"
    NOT_EXISTS_STR = "Όχι"

    EXISTS = 1
    NOT_EXISTS = 0

    SEND = 0
    RECEIVE = 1
    def __setattr__(self, attribute, val):
        """
        Set new constants and prevent from changing values from already
        set constants
        """

        if hasattr(self, attribute):
            raise ValueError, 'Constant %s already has a value' % attribute

        self.__dict__[attribute] = val
