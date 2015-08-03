import json

#: end of the header
end_of_header = '\r\n\r\n'

#: limit size of header, once the connection sends too many bytes and
#: exceeds this limit, we will lose the connection
HEADER_LIMIT = 1024


def parseHeader(data):
    """Parse header from a chunk of data and return (header, remain data)

    """
    if end_of_header not in data:
        return
    header_data, other = data.split(end_of_header)
    header = json.loads(header_data)
    return header, other


def makeHeader(header):
    """Make a header request

    """
    data = json.dumps(header) + end_of_header
    return data


class ParserMixIn(object):

    def __init__(self):
        self._buffer = []
        self._buffer_size = 0
        #: are we streaming
        self.streaming = False

    def handleHeader(self, header):
        raise NotImplemented

    def handleBody(self, data):
        raise NotImplemented

    def dataReceived(self, data):
        if not self.streaming:
            self._buffer.append(data)
            self._buffer_size += len(data)
            if self.end_of_header in data:
                header_data = self.getBuffer()
                # we don't need the buffer any more
                del self._buffer
                del self._buffer_size
                header, other = parseHeader(header_data)
                self.handleRequest(header)
                self.logger.warn('Received unexpected data %r', other)
            else:
                if self._buffer_size > self.HEADER_LIMIT:
                    self.sendHeader(dict(error='bad request'))
                    self.close('Header too long')
        else:
            self.logger.warn('Received unexpected data %r', data)
