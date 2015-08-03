import hashlib
import json
import logging
import os
import urllib

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.web.client import getPage

from nowin_core.patterns import observer
from nowin_core.source import command


def errorToUnicode(error):
    """Convert error to unicode string

    """
    if not error.args:
        return u''
    if os.name == 'nt':
        import locale
        _, encoding = locale.getdefaultlocale()
        return error.args[0].decode(encoding)
    return error.args[0]


class ServiceNotAvailable(Exception):

    """Service not available error

    """


class SourceProtocol(command.CommandReceiver):
    authorized = False
    listenerCount = 0
    closed = False
    phase = None
    challenge = None
    salt = None

    def __init__(self, user, password, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        command.CommandReceiver.__init__(self)

        self.user = user
        self.password = password
        self.offset = 0

        # called when the connection is made
        self.connectingMadeEvent = observer.Subject()
        # called when client lost connection with argument (reason)
        self.connectionLostEvent = observer.Subject()
        # called when on line listeners changed
        self.listenerCountChangedEvent = observer.Subject()
        # called when the user is authorized
        self.authorizedEvent = observer.Subject()
        # called when data is written
        self.dataWrittenEvent = observer.Subject()
        # called when data is sent to peer
        self.dataSentEvent = observer.Subject()
        # called an error occurs, with argument (error number, error msg)
        self.errorEvent = observer.Subject()

    def close(self):
        if not self.closed:
            self.transport.loseConnection()
            self.closed = True
            self.authorized = False
            self.phase = None
            self.listenerCount = 0

    def connectionMade(self):
        command.CommandReceiver.connectionMade(self)
        self.logger.info('Connected')
        version = """MR.DJ %(major)d/%(minor)d\r\n""" % dict(
            major=self.factory.major,
            minor=self.factory.minor
        )
        self.transport.write(version)
        self.phase = 'version'

    def _sendResponse(self):
        if self.salt and self.challenge:
            h = hashlib.sha1()
            h.update(self.password + self.salt)
            hashed = h.hexdigest()

            h = hashlib.sha1()
            h.update(hashed + self.challenge)
            hashed = hashed = h.hexdigest()

            self.sendCommand('Response', hashed)
            self.logger.info('Send response')

    def commandReceived(self, cmd, data):
        self.logger.debug('Received command %s with data %s', cmd, data)

        def authentication():
            if cmd.lower() == 'challenge':
                self.logger.info('Received challenge %s', data)
                self.challenge = data
                self._sendResponse()
            elif cmd.lower() == 'salt':
                self.logger.info('Received salt %s', data)
                self.salt = data
                self._sendResponse()
            elif cmd.lower() == 'authorized':
                self.logger.info('Authorized as %s', data)
                self.user = data
                self.authorized = True
                self.phase = 'broadcasting'
                self.authorizedEvent()
                # replace the writeSomeData of transport with ours
                self.transport._originalWriteSomeData = \
                    self.transport.writeSomeData
                self.transport.writeSomeData = self._writeSomeData
                self.transport._originalWrite = self.transport.write
                self.transport.write = self._write

        def broadcasting():
            if cmd.lower() == 'listener-count':
                self.listenerCount = int(data)
                self.logger.info(
                    'Update listener count to %d', self.listenerCount)
                self.listenerCountChangedEvent()

        phaseMap = dict(
            authentication=authentication,
            broadcasting=broadcasting
        )
        phaseMap[self.phase]()

        if cmd.lower() == 'error':
            number, msg = data.split(' ', 1)
            number = int(number)
            self.logger.error('Error from server %d %s', number, msg)
            self.errorEvent((number, msg))
            self.close()

    def rawDataReceived(self, data):
        self.logger.debug('Received data %r', data)
        try:
            line, remain = data.split('\r\n', 1)
            if line == 'OK':
                self.setChannelMode(remain)
                self.sendCommand('User', self.user)
                self.phase = 'authentication'
            elif line == 'OLD_PROTOCOL':
                # old protocol
                self.logger.error('The protocol is too old')
                self.errorEvent(100, 'The protocol is too old')
                self.close()
            elif line == 'BAD_PROTOCOL':
                # bad protocol
                self.logger.error('The protocol is bad')
                self.errorEvent(101, 'Bad protocol')
                self.close()
        except ValueError:
            # Unknown protocol
            self.logger.error('Unknown protocol')
            self.errorEvent(102, 'Unknown protocol')
            self.close()
        return

    def connectionLost(self, reason):
        self.logger.debug('Raw reason: %r', reason)
        if self.closed:
            return
        message = errorToUnicode(reason.value)
        self.logger.info('Connection lost with reason %s', message)
        self.authorized = False
        self.connectionLostEvent(message)

    def _writeSomeData(self, data):
        """This function is used to override the writeSomeData of transport

        """
        sent = self.transport._originalWriteSomeData(data)
        self.dataSentEvent(sent)
        return sent

    def _write(self, data):
        self.dataWrittenEvent(len(data))
        return self.transport._originalWrite(data)

    def write(self, data):
        self.logger.log(logging.NOTSET, 'Write audio %d bytes', len(data))
        self.send(self.aduio_channel, data)
        self.offset += len(data)

    def updateMusicInfo(self, tag):
        tag['offset'] = self.offset
        for key, value in tag.iteritems():
            if value is None:
                tag[key] = ''
            else:
                tag[key] = value
        self.logger.info('Update music info %r', tag)
        if self.factory.major == 2:
            data = json.dumps(tag)
        else:
            import types
            for key, value in tag.iteritems():
                if isinstance(value, types.UnicodeType):
                    tag[key] = value.encode('utf8')
            data = urllib.urlencode(tag)
        self.sendCommand('Music-Info', data)


class SourceClient(ClientFactory):
    major = 1
    minor = 0

    def __init__(self,
                 addressFile='http://now.in/broadcast_server_address',
                 force_host=None,
                 force_port=None,
                 logger=None
                 ):
        """

        @param addressFile: address of the web page contains ip and port of
            broadcast server
        @param host: host of broadcast server to connect, if the value is not
            None, this value will be used rather than addressFile
        @param port: port of broadcast server
        """
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        self.addressFile = addressFile
        self.force_host = force_host
        self.force_port = force_port
        self.client = None

        # called when the client is connecting
        self.connectingEvent = observer.Subject()
        # called when the connection is made
        self.connectingMadeEvent = observer.Subject()
        # called when the connection is failed
        self.connectionFailedEvent = observer.Subject()
        # called when client lost connection with argument (reason)
        self.connectionLostEvent = observer.Subject()
        # called when user logout
        self.logoutEvent = observer.Subject()
        # called when on line listeners changed
        self.listenerCountChangedEvent = observer.Subject()
        # called when the user is authorized
        self.authorizedEvent = observer.Subject()
        # called when data is written
        self.dataWrittenEvent = observer.Subject()
        # called when data is sent to peer
        self.dataSentEvent = observer.Subject()
        # called an error occurs, with argument (error number, error msg)
        self.errorEvent = observer.Subject()

        self.connectionLostEvent.subscribe(self._onConnectionLost)

    def _getListenerCount(self):
        if self.client and self.client.authorized:
            return self.client.listenerCount
        return 0
    listenerCount = property(_getListenerCount)

    def _getAuthorized(self):
        return self.client and self.client.authorized
    authorized = property(_getAuthorized)

    def _onConnectionLost(self, reason):
        self.client = None

    def buildProtocol(self, addr):
        self.client = SourceProtocol(self.user, self.password)
        self.client.factory = self
        self.client.connectingMadeEvent.subscribe(self.connectingMadeEvent)
        self.client.connectionLostEvent.subscribe(self.connectionLostEvent)
        self.client.listenerCountChangedEvent.subscribe(
            self.listenerCountChangedEvent)
        self.client.authorizedEvent.subscribe(self.authorizedEvent)
        self.client.dataWrittenEvent.subscribe(self.dataWrittenEvent)
        self.client.dataSentEvent.subscribe(self.dataSentEvent)
        self.client.errorEvent.subscribe(self.errorEvent)
        return self.client

    def clientConnectionFailed(self, connector, reason):
        message = errorToUnicode(reason.value)
        # log.error('Connection failed with reason %s', message)
        self.connectionFailedEvent(message)
        self.client = None

    def _getHost(self):
        if self.force_host:
            return self.force_host, self.force_port

        def handleAddress(result):
            self.logger.info('Get broadcast server info %s', result)
            if not result.strip():
                return ServiceNotAvailable('Service not avaiable')
            # old protocol
            if '\n' not in result:
                self.major = 1
                self.minor = 0
                address = result
                self.logger.info('Use old protocol 1.0')
            else:
                parts = result.split('\n')
                address = parts[0]
                version = parts[1]
                major, minor = version.split()
                self.major = int(major)
                self.minor = int(minor)
                self.logger.info('Use new protocol %s.%s',
                                 self.major, self.minor)
            host, port = address.split(':')
            host = host
            port = int(port)
            return host, port

        def handleFailed(error):
            self.logger.error('Failed to get broadcast server address')
            self.logger.exception(error)
            self.client.connectionLostEvent(error.value.message)
        d = getPage(self.addressFile)
        d.addCallback(handleAddress)
        d.addErrback(handleFailed)
        return d

    def login(self, user, password):
        """Login to server

        @param user: user to login
        @param password: password of user account
        """
        self.user = user
        self.password = password

        def connect(result):
            host, port = result
            self.logger.info('Connect to %s:%d', host, port)
            reactor.connectTCP(host, port, self)
            self.connectingEvent()
            return result
        d = defer.maybeDeferred(self._getHost)
        d.addCallback(connect)
        return d

    def logout(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.logoutEvent()

    def write(self, data):
        if self.authorized:
            self.client.write(data)

    def updateMusicInfo(self, tag):
        if self.authorized:
            self.client.updateMusicInfo(tag)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    client = SourceClient()
    client.login('victor', '')
    client.updateMusicInfo(dict())
    reactor.run()
