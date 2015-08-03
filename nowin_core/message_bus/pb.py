import logging

from twisted.cred import credentials
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.spread import pb


def remoteCallback(func):
    class Callback(pb.Referenceable):

        def __call__(self, *args, **kwargs):
            return func(*args, **kwargs)

        def remote_call(self, event, data):
            try:
                return func(event, data)
            except Exception:
                logger = logging.getLogger(__name__)
                logger.error('Remote callback failed', exc_info=True)
    return Callback()


class PBMessageBus(object):

    def __init__(self, hosts, logger=None):
        """

        """
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        self.hosts = hosts
        self.conn = None

        self.factory = pb.PBClientFactory()
        self.avatar = None

        self.logger.info('Create message bus with hosts %s', self.hosts)

    def onDisconnected(self, avatar):
        self.logger.info('Disconnected by peer')
        del self.avatar

    @inlineCallbacks
    def login(self, user, password):
        """Login message bus

        """
        self.logger.debug('Logging in as %s ...', user)
        host = self.hosts[0]
        reactor.connectTCP(host[0], host[1], self.factory)
        cerd = credentials.UsernamePassword(user, password)
        self.avatar = yield self.factory.login(cerd)
        self.avatar.notifyOnDisconnect(self.onDisconnected)
        self.logger.info('Logged in Message Bus Server as %s', user)

    @inlineCallbacks
    def send(self, dest, data):
        """Send data to message bus

        """
        self.logger.debug('Sending data to %s ...', dest)
        yield self.avatar.callRemote('advertise', dest, data)
        self.logger.info('Sent data to %s', dest)

    @inlineCallbacks
    def subscribe(self, dest, callback):
        """Subscribe to specific destination, the callback will be called when
        the there is message in the destination

        """
        dest = str(dest)
        self.logger.debug('Subscribing to %s ...', dest)
        callback = remoteCallback(callback)
        id = yield self.avatar.callRemote('watch', dest, callback)
        self.logger.info('Subscribed to %s with id %s', dest, id)
        returnValue(id)

    @inlineCallbacks
    def unsubscribe(self, id):
        """Unsubscribe from message bus

        """
        self.logger.debug('Unsubscribe... from %s', id)
        yield self.avatar.callRemote('stopWatch', id)
        self.logger.info('Unsubscribed from %s', id)

    @inlineCallbacks
    def close(self):
        """Close connection to message bus

        """
        self.logger.debug('Closing message bus ...')
        yield self.factory.disconnect()
        self.logger.info('Closed message bus')
