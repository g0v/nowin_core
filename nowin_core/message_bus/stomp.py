import logging

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import maybeDeferred
from twisted.internet.defer import returnValue

from nowin_core.patterns import observer
from nowin_core.stomp import async_client


class STOMPMessageBus(object):

    def __init__(
        self,
        host,
        user,
        password=None,
        logger=None
    ):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        self.host = host
        self.user = user
        self.password = password

        self.client = None

        # called when we are authorized
        self.auth_event = observer.Subject()
        # called when connection lost
        self.conn_lost_event = observer.Subject()
        # called when connection to host failed
        self.conn_failed_event = observer.Subject()

        #: is this connection closed
        self.closed = False

        #: client event subscribe ids
        self._sub_ids = []

        self.logger.info('Create message bus, host=%s, user=%s',
                         self.host, self.user)

    def handleConnLost(self):
        """Called when connection lost

        """
        self.close()
        self.conn_lost_event()

    def handleAuth(self):
        """Called when we are authorized

        """
        self.auth_event()

    @inlineCallbacks
    def connect(self):
        """Connect to peer

        """
        from twisted.internet.protocol import ClientCreator

        self.closed = False

        if self.client is not None:
            self.logger.warn('Already connected')
            returnValue(None)

        self.logger.debug('Logging in as %s ...', self.user)
        creator = ClientCreator(reactor, async_client.STOMPClient)
        try:
            self.logger.info('Connecting to %s', self.host)
            self.client = yield creator.connectTCP(*self.host)
        except Exception, e:
            self.logger.info('Failed to connect to %s', self.host)
            self.client = None
            self.conn_failed_event()
            returnValue(e)

        # already closed
        if self.closed:
            self.logger.warn('Abort connection')
            self.client.close()
            self.client = None
            return

        self._sub_ids.append(
            self.client.conn_lost_event.subscribe(self.handleConnLost))
        self._sub_ids.append(
            self.client.auth_event.subscribe(self.handleAuth))

        try:
            yield self.client.login(self.user, self.password)
        except Exception, e:
            self.logger.info('Failed to login as %s', self.user)
            self.logger.exception(e)
            self.conn_failed_event()
            returnValue(e)
        self.logger.info('Login as %s', self.user)

    @inlineCallbacks
    def send(self, dest, data):
        """Send data to message bus

        """
        if self.client is None:
            self.logger.warn('Not connected, ignore send cmd to %s', dest)
            returnValue(None)
        dest = str(dest)
        self.logger.debug('Sending %s bytes to %s ...', len(data), dest)
        yield maybeDeferred(self.client.send, dest, data)
        self.logger.info('Sent %s bytes to %s', len(data), dest)

    @inlineCallbacks
    def subscribe(self, dest, callback):
        """Subscribe to specific destination, the callback will be called when
        the there is message in the destination

        """
        if self.client is None:
            self.logger.warn('Not connected, ignore subscribe cmd to %s', dest)
            returnValue(None)
        dest = str(dest)
        self.logger.debug('Subscribing to %s ...', dest)
        yield maybeDeferred(self.client.subscribe, dest, callback)
        self.logger.info('Subscribed to %s', dest)

    @inlineCallbacks
    def unsubscribe(self, dest):
        """Unsubscribe from message bus

        """
        if self.client is None:
            self.logger.warn('Not connected, ignore Unsubscribe cmd to %s',
                             dest)
            returnValue(None)
        self.logger.debug('Unsubscribe... from queue %s', dest)
        yield maybeDeferred(self.client.subscribe, dest)
        self.logger.info('Unsubscribed from queue %s', dest)

    def close(self):
        """Close connection to message bus

        """
        if self.client is None or self.closed:
            self.logger.warn('Already closed')
            return
        self.logger.debug('Closing message bus ...')
        for sid in self._sub_ids:
            sid.unsubscribe()
        self._sub_ids = []
        self.client.close()
        self.client = None
        self.closed = True
        self.logger.info('Closed message bus')
