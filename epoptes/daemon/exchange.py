"""
Global registry type stuff
"""

knownClients = {}
knownGUIs = []


def clientConnected(handle, client):
    print "Client connected: %s" % handle.encode("utf-8")
    knownClients[handle] = client
    for gui in knownGUIs:
        gui.clientConnected(handle)


def clientDisconnected(handle):
    if handle not in knownClients:
        print "Disconnect from unknown client: %s" % handle.encode("utf-8")
        return

    print "Client disconnected: %s" % handle.encode("utf-8")
    del knownClients[handle]
    for gui in knownGUIs:
        gui.clientDisconnected(handle)
