import struct

__all__ = [
    'makeFrames',
    'Parser'
]

#: version of source protocol
version = (1, 0)
#: audio channel
aduio_channel = 'audio'
#: command channel
cmd_channel = 'cmd'


def _makeFrame(channel, data):
    assert len(channel) <= 255, 'Length of channel name should be less ' \
                                'than 255'
    assert len(channel), 'Length of channel should not be 0'
    assert len(data) <= 255, 'Length of data should be less than 255'
    assert len(data), 'Length of data should not be 0'
    format = '>B%dsBB%ds' % (len(channel), len(data))
    bin = struct.pack(format, len(channel), channel, 0, len(data), data)
    return bin


def makeFrames(channel, data, type=0):
    """Make frames

    split data into frames if it is too long, and return a list
    of frames

    """
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        yield _makeFrame(channel, chunk)


class Parser(object):

    def __init__(self, remain=''):
        self._buffer = remain
        self._parsingPhase = 0
        self._channelNameLength = None
        self._channelName = None
        self._channelDataType = None
        self._channelDataLength = None

    def getBuffer(self):
        return self._buffer

    def feed(self, data):
        self._buffer += data

    def getFrame(self):
        """Parse data, get and return frame, return (channel id, data) tuple

        """
        frame = [None]

        # read the channel name length
        def phase0():
            (self._channelNameLength,) = struct.unpack('B', self._buffer[:1])
            self._buffer = self._buffer[1:]
            self._parsingPhase = 1

        # read the channel name
        def phase1():
            # need more data
            if len(self._buffer) < self._channelNameLength:
                return True
            self._channelName = self._buffer[:self._channelNameLength]
            self._buffer = self._buffer[self._channelNameLength:]
            self._parsingPhase = 2

        # read the type of channel data
        def phase2():
            (self._channelDataType,) = struct.unpack('B', self._buffer[:1])
            self._buffer = self._buffer[1:]
            self._parsingPhase = 3

        # read the length of channel data
        def phase3():
            (self._channelDataLength,) = struct.unpack('B', self._buffer[:1])
            self._buffer = self._buffer[1:]
            self._parsingPhase = 4

        # read the channel data
        def phase4():
            if len(self._buffer) < self._channelDataLength:
                return True

            channelName = self._channelName
            channelData = self._buffer[:self._channelDataLength]
            self._buffer = self._buffer[self._channelDataLength:]
            self._parsingPhase = 0

            self._channelName = None
            self._channelNameLength = None
            self._channelDataLength = None
            self._channelDataType = None
            frame[0] = (channelName, channelData)

        phaseMap = {
            0: phase0,
            1: phase1,
            2: phase2,
            3: phase3,
            4: phase4
        }

        while self._buffer and not frame[0]:
            func = phaseMap[self._parsingPhase]
            if func():
                break
        return frame[0]
