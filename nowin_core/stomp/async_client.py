import json
import logging
import uuid

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import Protocol

from nowin_core.patterns import observer
from nowin_core.stomp import protocol


class STOMPClient(Protocol):

    #: initial state
    STATE_INIT = 0

    #: login state
    STATE_LOGIN = 1

    #: connected state
    STATE_CONNECTED = 2

    def __init__(self, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        #: parser for STOMP protocol
        self.parser = protocol.Parser()
        #: state of current connection
        self.state = self.STATE_INIT
        #: map channel name to callback functions
        self.callbacks = {}
        #: session id of current connection
        self.session_id = None

        #: defer for login
        self._login_defer = None

        #: map receipt id to defers
        self.receipts = {}

        # called when connection lost
        self.conn_lost_event = observer.Subject()
        # called when we are authorized
        self.auth_event = observer.Subject()

    def dataReceived(self, data):
        """Called when data received

        """
        self.parser.feed(data)
        while True:
            frame = self.parser.getFrame()
            if frame is None:
                break
            self.processFrame(frame)

    def connectionMade(self):
        """Called when connection made

        """

    def connectionLost(self, reason):
        """Connection lost

        """
        self.conn_lost_event()
        self.logger.info('Connection lost with session %s', self.session_id)

    def login(self, user='', password=''):
        """Login to STOMP server

        """
        frame = protocol.Frame('CONNECT', dict(login=user, passcode=password))
        self.transport.write(frame.pack())
        self.state = self.STATE_LOGIN
        self._login_defer = defer.Deferred()
        self.logger.info('Logging in as %r', user)
        return self._login_defer

    def processFrame(self, frame):
        """Called to process a frame from peer

        """
        if self.state == self.STATE_LOGIN:
            if frame.command == 'CONNECTED':
                self.session_id = frame.headers['session']
                self.state = self.STATE_CONNECTED
                self._login_defer.callback(None)
                self.auth_event()
                self.logger.info('Connected as session %s', self.session_id)
            elif frame.command == 'ERROR':
                self.logger.error('[%s] Error %r',
                                  self.session_id, frame.body)
                error = Exception(frame.body)
                self._login_defer.errback(error)
            else:
                msg = 'Unexpected command %s' % frame.command
                self.logger.error(msg)
                error = Exception(msg)
                self._login_defer.errback(error)
        elif self.state == self.STATE_CONNECTED:
            if frame.command == 'MESSAGE':
                dest = frame.headers['destination']
                callback = self.callbacks[dest]
                callback(dest, json.loads(frame.body))
            elif frame.command == 'RECEIPT':
                # notify the deferred that message was receipted
                rid = frame.headers.get('receipt-id')
                if rid is not None:
                    d = self.receipts.get(rid)
                    if d:
                        d.callback(1)
                        del self.receipts[rid]
            elif frame.command == 'ERROR':
                self.logger.error('[%s] Error %r',
                                  self.session_id, frame.body)
            else:
                self.logger.error('[%s] Unexpected command %s with '
                                  'headers=%r, body=%r',
                                  self.session_id, frame.command,
                                  frame.headers, frame.body)

    def subscribe(self, dest, callback):
        """Subscribe to a message queue `dest` with `callback` function

        """
        frame = protocol.Frame('SUBSCRIBE', dict(destination=dest))
        self.transport.write(frame.pack())
        self.callbacks[dest] = callback
        self.logger.info('[%s] Subscribed to %s', self.session_id, dest)

    def unsubscribe(self, dest):
        """Unsubscribe from a message queue

        """
        frame = protocol.Frame('UNSUBSCRIBE', dict(destination=dest))
        self.transport.write(frame.pack())
        del self.callbacks[dest]
        self.logger.info('[%s] Unsubscribed from %s', self.session_id, dest)

    def send(self, dest, data, receipt=False, timeout=5):
        """Send data to message queue

        """
        data = json.dumps(data)
        headers = dict(destination=dest)
        d = None
        if receipt:
            rid = uuid.uuid4().hex
            headers['receipt'] = rid
            d = defer.Deferred()
            self.receipts[rid] = d

            def handle_timeout():
                d = self.receipts.get(rid)
                if d is not None:
                    d.errback(RuntimeError('Time out'))
                    del self.receipts[rid]

            reactor.callLater(timeout, handle_timeout)

        frame = protocol.Frame('SEND', headers, data)
        self.transport.write(frame.pack())
        self.logger.info('[%s] Sent %d bytes data to %s',
                         self.session_id, len(data), dest)
        return d

    def close(self):
        """Close connection to server

        """
        frame = protocol.Frame('DISCONNECT')
        self.transport.write(frame.pack())
        self.transport.loseConnection()
        self.logger.info('[%s] Connection closed', self.session_id)

if __name__ == '__main__':
    from twisted.internet.protocol import ClientCreator

    logging.basicConfig(level=logging.INFO)

    def gotProtocol(p):
        p.login('a', 'b')

        def foo(dest, data):
            print dest, data

        p.subscribe('abc', foo)
        p.send('abc', 'hello')
        return p

    creator = ClientCreator(reactor, STOMPClient)
    d = creator.connectTCP("localhost", 61613)
    d.addCallback(gotProtocol)
    reactor.run()
