from twisted.protocols.basic import LineReceiver

from nowin_core.source import channel


class CommandReceiver(channel.ChannelReceiver):

    def __init__(self):
        self.lineReceiver = LineReceiver()
        self.lineReceiver.lineReceived = self.lineReceived

    def lineReceived(self, line):
        cmd, data = line.split(':', 1)
        self.commandReceived(cmd.strip(), data.strip())

    def commandReceived(self, cmd, data):
        raise NotImplementedError

    def sendCommand(self, cmd, data):
        return self.send(self.cmd_channel, '%s: %s\r\n' % (cmd, data))

    def channeReceived(self, channel, type, data):
        if channel == self.cmd_channel:
            self.lineReceiver.dataReceived(data)
