from twisted.protocols import amp


class ClientConnected(amp.Command):
    arguments = [('handle', amp.Unicode())]
    response = []


class ClientDisconnected(amp.Command):
    arguments = [('handle', amp.Unicode())]
    response = []


class EnumerateClients(amp.Command):
    arguments = []
    response = [('handles', amp.ListOf(amp.Unicode()))]


class ClientCommand(amp.Command):
    arguments = [('handle', amp.Unicode()),
                 ('command', amp.Unicode())]

    response = [('result', amp.String()),
                ('filename', amp.String())]
