import struct

__all__ = [
    'makeFrames',
    'Parser'
]

#: version of source protocol
version = (2, 0)
#: audio channel
aduio_channel = 0
#: command channel
cmd_channel = 1


def makeFrames(channel, data, type=0):
    """Make frames

    split data into frames if it is too long, and return a list
    of frames

    """
    assert channel >= 0 and channel <= 255
    limit = 65535
    frames = []
    for i in range(0, len(data), limit):
        chunk = data[i:i + limit]
        frame = struct.pack('BBH%ds' % len(chunk),
                            channel, type, len(chunk), chunk)
        frames.append(frame)
    return frames


class Parser(object):

    # phase for header
    _phase_header = 0
    # phase for data
    _phase_data = 1

    def __init__(self, remain=''):
        self._buffer = [remain]
        self._length = len(remain)
        self._phase = self._phase_header
        self._channel_id = None
        self._channel_type = None
        self._channel_length = None

    def getBuffer(self):
        return ''.join(self._buffer)

    def feed(self, data):
        self._buffer.append(data)
        self._length += len(data)

    def getFrame(self):
        """Parse data, get and return frame, return (channel id, data) tuple

        """
        if self._phase == self._phase_header:
            # we have enough data to parse header
            if self._length >= 4:
                data = ''.join(self._buffer)
                self._channel_id, self._channel_type, self._channel_length = \
                    struct.unpack('BBH', data[:4])
                self._buffer = [data[4:]]
                self._length = len(self._buffer[0])
                self._phase = self._phase_data
        if self._phase == self._phase_data:
            # we have enough data body to parse
            if self._length >= self._channel_length:
                data = ''.join(self._buffer)
                body = data[:self._channel_length]
                self._buffer = [data[self._channel_length:]]
                self._length = len(self._buffer[0])
                self._phase = self._phase_header
                return self._channel_id, body
