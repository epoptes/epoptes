#-*- coding: utf-8 -*-

# ['ltsp123', '00-1b-24-89-65-d6', '127.0.0.1:46827', '10.160.31.126:44920', 
#  'thin', 'user3', <gtk.gdk.Pixbuf>, '10.160.31.123', 'user (ltsp123)']
C_HOSTNAME = 0
C_MAC = 1
C_SESSION_HANDLE = 2
C_SYSTEM_HANDLE = 3
C_TYPE = 4
C_USER = 5
C_PIXBUF = 6
C_IP = 7
C_VIEW_STYLE = 8

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
