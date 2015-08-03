import logging

from twisted.internet.interfaces import IPullProducer
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from zope.interface import implements

from nowin_core.patterns import observer
from nowin_core.stream import base


class StreamProtocol(Protocol):

    """Stream protocol is a very simple protocol for sending audio stream data
    only.

    We employ this protocol in order to replace original HTTP connections
    between broadcast and proxy.  Why we invite another wheel, and why to
    replace the HTTP, here is those reasons

    * HTTP is too complex - All we need is to find is there such a audio
      resource and transfer the audio data stream. Also, we want to migrate
      our broadcast server cross process on the fly, HTTP modules provided
      by Twisted is too complex and too dirty to dump and load the state.

    * HTTP makes some overhead - HTTP may use transfer-encoding to transfer
      audio data, which might be kind of overhead.

    And following are design goals:

    * Simple - We don't want to invent another HTTP, it should be simple,
      and do only exactly what we need

    * Portable - We should able to implement this protocol everywhere, not only
      in Python.

    * Efficient - There should not be too many overhead to send package and
      parse package

    The idea of design is simple, we use JSON as header, it should be
    easy-to-parse for almost any language. And the audio data is in raw
    binary format just behind the header.

    Following is the flow of how a client make a connection and get the audio
    stream

    1. Client send a request header to server

        Client -> Server:

        JSON:
            {
                'name': resource name
            }

        Header ends with \r\n\r\n

    2. Server send response

       If there is no such audio resource on server, here the response should
       be

       Server -> Client

       JSON:
           {
               'name': resource name,
               'result': 'not_found',
           }

       And close the connection.

       If the audio resource did exist, then the response should be

       Server -> Client

       JSON:
           {
               'name': resource name,
               'result': 'found',
               'begin_offset': begin offset of audio data,
               (some extra information should goes here)
           }

       Same as the request, all header ends with \r\n\r\n
       For now, the client should be ready to receive audio data.

    3. Send the audio data stream

    By now, the connection is made, then server can send the audio data to
    client

    Server -> Client
        (audio binary data)

    """
    implements(IPullProducer)

    def __init__(self, get_res_func, session_no=0, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        #: function for getting resource
        self.get_res_func = get_res_func
        #: session number
        self.session_no = session_no
        #: buffer for header
        self._buffer = []
        self._buffer_size = 0
        #: does the client needs more data
        self._hungry = True
        #: is this stream already streaming data
        self.streaming = False
        #: name of audio resource
        self.name = None
        #: offset in audio stream
        self.offset = 0
        #: is this connection closed?
        self.is_closed = False
        #: audio stream
        self.audio_stream = None

        #: called when connection lost
        self.conn_lost_event = observer.Subject()
        #: called when data write with argument (data)
        self.data_write_event = observer.Subject()

    def __repr__(self):
        return '<%s session=%s, addr=%s>' % (
            self.__class__.__name__,
            self.session_no,
            self.remote_address
        )

    @property
    def remote_address(self):
        """Remote address

        """
        return self.transport.getPeer()

    def getBuffer(self):
        data = ''.join(self._buffer)
        self._buffer = [data]
        return data

    def connectionMade(self):
        self.logger.info('New connection %s', self)

    def stopProducing(self):
        self.conn_lost_event()
        self.logger.info('%s stop producing', self)

    def resumeProducing(self):
        """Called when peer needs more data

        """
        self._hungry = True
        self.produce()

    def produce(self):
        """Produce data and send to peer if available

        """
        if not self._hungry:
            return

        # this listener out of buffer window
        if self.offset < self.audio_stream.base:
            self.logger.warn('%s out of buffer window', self)
            self.close('Out of buffer', event=True)
            return

        block, self.offset = self.audio_stream.read(self.offset)
        if block:
            self.transport.write(block)
            self.data_write_event(block)
            self._hungry = False

    def sendHeader(self, header):
        """Send header to peer

        """
        self.transport.write(base.makeHeader(header))

    def handleRequest(self, header):
        name = header['name']
        res = self.get_res_func(name)
        # there is no such resource
        if res is None:
            self.sendHeader(dict(name=name, result='not_found'))
            self.close(event=True)
            return
        res.add(self)
        # set the offset to middle of the buffer, in order to avoid
        # running out of data too soon
        self.offset = res.audio_stream.middle
        self.audio_stream = res.audio_stream
        header = dict(name=name, result='found', begin_offset=self.offset)
        self.sendHeader(header)
        # register self as the pull producer
        self.transport.registerProducer(self, False)
        self.streaming = True
        self.logger.info('%s started streaming', self)

    def dataReceived(self, data):
        if not self.streaming:
            self._buffer.append(data)
            self._buffer_size += len(data)
            if base.end_of_header in data:
                header_data = self.getBuffer()
                # we don't need the buffer any more
                del self._buffer
                del self._buffer_size
                header, other = base.parseHeader(header_data)
                self.handleRequest(header)
                if other:
                    self.logger.warn('Received unexpected data %r', other)
            else:
                if self._buffer_size > base.HEADER_LIMIT:
                    self.sendHeader(dict(error='bad request'))
                    self.close('Header too long', event=True)
        else:
            self.logger.warn('Received unexpected data %r', data)

    def close(self, reason=None, event=False):
        """Close this stream by server side

        """
        if self.is_closed:
            return
        self.transport.unregisterProducer()
        self.transport.loseConnection()
        self.is_closed = True
        if event:
            self.conn_lost_event()
        self.logger.info('Close stream %s with reason %s', self, reason)


class AudioResource(object):

    def __init__(self, name, audio_stream, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        #: name of this resource
        self.name = name
        #: audio stream
        self.audio_stream = audio_stream
        #: set of all streams in this audio resource
        self.streams = set()
        #: called when data write with argument (data)
        self.data_write_event = observer.Subject()

    def handleClosedStream(self, stream):
        self.remove(stream)

    def add(self, stream):
        self.streams.add(stream)
        stream.conn_lost_event.subscribe(
            lambda: self.handleClosedStream(stream))
        stream.data_write_event.subscribe(self.data_write_event)
        self.logger.info('Add stream %s to resource %s', stream, self)

    def remove(self, stream):
        self.streams.remove(stream)
        self.logger.info('Delete stream %s from resource %s', stream, self)

    def write(self, data):
        """Write audio data to all streams

        """
        self.audio_stream.write(data)
        [s.produce() for s in self.streams]

    def close(self, reason=None):
        [s.close('Resource closed') for s in self.streams]
        self.streams = set()
        self.logger.info('Close audio resource %s with reason %s',
                         self, reason)


class StreamFactory(Factory):

    protocol = StreamProtocol

    def __init__(self, audio_stream_factory, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.audio_stream_factory = audio_stream_factory
        #: mapping name to audio resources
        self.resources = {}
        #: current session number
        self.session_no = 0
        #: triggered when data was wrote with argument (data string)
        self.data_write_event = observer.Subject()

    def buildProtocol(self, addr):
        s = self.session_no
        p = self.protocol(self.getResource, s)
        p.factory = self
        self.session_no += 1
        return p

    def getResource(self, name):
        """Get resource and return

        """
        return self.resources.get(name)

    def getCountOfStreams(self):
        """Get total count of streams (connections)

        """
        sum = 0
        for res in self.resources.itervalues():
            sum += len(res.streams)
        return sum

    def add(self, name):
        """Add audio resource

        """
        assert name not in self.resources
        audio_stream = self.audio_stream_factory()
        resource = AudioResource(name, audio_stream)
        resource.data_write_event.subscribe(self.data_write_event)
        self.resources[name] = resource
        return resource

    def remove(self, name):
        """Delete audio resource

        """
        resource = self.resources[name]
        del self.resources[name]
        return resource

    def write(self, name, data):
        """Write audio data to radio

        """
        res = self.resources[name]
        return res.write(data)

    def close(self):
        """Close all resources

        """
        [res.close('Closed by factory') for res in self.resources]

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from twisted.internet import reactor

    def makeAudioStream():
        from nowin_core.memory.audio_stream import AudioStream
        return AudioStream()

    factory = StreamFactory(makeAudioStream)

    def sendData(self):
        res = factory.getResource('test')
        res.write('hello' * 1000)

    res = factory.addResource('test')
    res.write('hello' * 1000)
    reactor.listenTCP(5566, factory)
    reactor.run()
