import logging

from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol

from nowin_core.patterns import observer
from nowin_core.stream import base
from nowin_core.utils import setKeepAlive


class StreamClientProtocol(Protocol):

    def __init__(self, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self._buffer = []
        self._buffer_size = 0
        self.streaming = False
        self.is_closed = False
        self.begin_offset = 0

    def sendHeader(self, header):
        """Send header to peer

        """
        self.transport.write(base.makeHeader(header))

    def getBuffer(self):
        data = ''.join(self._buffer)
        self._buffer = [data]
        return data

    def connectionMade(self):
        if self.factory.keep_alive_opts is not None:
            try:
                setKeepAlive(self.transport, **self.factory.keep_alive_opts)
            except Exception, e:
                self.logger.error('Failed to set keep alive')
                self.logger.exception(e)
        # send request
        self.sendHeader(dict(name=self.factory.name))

    def audioDataReceived(self, data):
        self.factory.audio_received_event(data)

    def handleResponse(self, header):
        result = header['result']
        if result == 'not_found':
            self.factory.conn_failed_event()
            return
        self.begin_offset = header.get('begin_offset', self.begin_offset)
        self.streaming = True
        self.factory.streaming_event()

    def dataReceived(self, data):
        if self.is_closed:
            return
        if not self.streaming:
            self._buffer.append(data)
            self._buffer_size += len(data)
            if base.end_of_header in data:
                header_data = self.getBuffer()
                # we don't need the buffer any more
                del self._buffer
                del self._buffer_size
                header, other = base.parseHeader(header_data)
                self.handleResponse(header)
                if other:
                    self.audioDataReceived(other)
            else:
                if self._buffer_size > base.HEADER_LIMIT:
                    self.sendHeader(dict(error='bad request'))
                    self.close('Header too long')
        else:
            self.audioDataReceived(data)

    def close(self, reason=None):
        if self.is_closed:
            return
        self.is_closed = False
        self.transport.loseConnection()
        self.logger.info('%s closed with reason %s', self, reason)


class StreamClientFactory(ClientFactory):

    def __init__(
        self,
        host,
        port,
        name,
        keep_alive_opts=None,
        reactor=None,
        logger=None
    ):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.reactor = reactor
        self.host = host
        self.port = port
        self.name = name
        self.conn = None
        self.keep_alive_opts = keep_alive_opts

        #: Called when connection made
        self.conn_made_event = observer.Subject()
        #: Called when connection failed
        self.conn_failed_event = observer.Subject()
        #: Called when connection lost
        self.conn_lost_event = observer.Subject()
        #: Called when receive data with argument (audio data)
        self.audio_received_event = observer.Subject()
        #: Called when the streaming gets started
        self.streaming_event = observer.Subject()

    def __repr__(self):
        return '<%s host=%s:%s, name=%s>' % (
            self.__class__.__name__,
            self.host,
            self.port,
            self.name
        )

    @property
    def begin_offset(self):
        """Begin offset of audio stream

        """
        assert self.conn is not None
        return self.conn.begin_offset

    def start(self):
        """Start the streaming

        """
        assert self.conn is None
        reactor = self.reactor
        if self.reactor is None:
            from twisted.internet import reactor
        self.connector = reactor.connectTCP(self.host, self.port, self)

    def close(self):
        if self.conn:
            self.conn.close('Closed by local')

    def startedConnecting(self, connector):
        self.logger.info('Started to connect %s:%s', self.host, self.port)

    def buildProtocol(self, addr):
        self.conn = StreamClientProtocol()
        self.conn.factory = self
        self.conn_made_event()
        self.logger.info('%s connected', self.conn)
        return self.conn

    def clientConnectionLost(self, connector, reason):
        self.conn_lost_event()
        self.logger.info('Connection lost with reason, %s', reason)

    def clientConnectionFailed(self, connector, reason):
        self.conn_failed_event()
        self.logger.info('Connection failed with reason, %s', reason)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from twisted.internet import reactor
    factory = StreamClientFactory('127.0.0.1', 8002, 'victor')
    factory.start()
    reactor.run()
