import logging

from twisted.internet import protocol

from nowin_core.source import protocol_1_0
from nowin_core.source import protocol_2_0


class ChannelReceiver(protocol.Protocol):

    @property
    def aduio_channel(self):
        if self.factory.major == 1:
            return 'audio'
        return 0

    @property
    def cmd_channel(self):
        if self.factory.major == 1:
            return 'cmd'
        return 1

    def connectionMade(self):
        if self.factory.major == 1:
            self.source_protocol = protocol_1_0
        else:
            self.source_protocol = protocol_2_0
        self.parser = self.source_protocol.Parser()
        self.channelMode = False

    def dataReceived(self, data):
        logger = logging.getLogger(__name__)
        logger.debug('Received data: %r', data)
        if self.channelMode:
            self.parser.feed(data)
            while True:
                frame = self.parser.getFrame()
                if frame is None:
                    break
                channel, data = frame
                self.channeReceived(channel, 0, data)
        else:
            self.rawDataReceived(data)

    def setChannelMode(self, extra=''):
        self.channelMode = True
        if extra:
            return self.dataReceived(extra)

    def setRawMode(self):
        self.channelMode = False

    def rawDataReceived(self, data):
        """Override this for when raw data is received.
        """
        raise NotImplementedError

    def channeReceived(self, channel, data, type):
        """

        """
        raise NotImplementedError

    def send(self, channel, data):
        """Write data to channel

        """
        # logger = logging.getLogger(__name__)
        # logger.debug('Send command: %r: %r', channel, data)
        for frame in self.source_protocol.makeFrames(channel, data):
            self.transport.write(frame)
