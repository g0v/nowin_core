import logging
import uuid

from twisted.internet import reactor


class ReconnectSupervisor(object):

    """This supervisor watches message bus, if it gets disconnected, this
    object will try to reconnect

    msgbus is the MessageBus object to supervise, and delay is how many
    seconds to delay the reconnection
    """

    def __init__(self, msgbus, delay=1, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.delay = delay
        self.msgbus = msgbus
        self.msgbus.conn_failed_event.subscribe(self.handleConnFailed)
        self.msgbus.conn_lost_event.subscribe(self.handleConnLost)

    def handleConnFailed(self):
        """Called to handle connection failed event

        """
        self.logger.warn('Connection of %s failed, retry %s seconds later',
                         self.msgbus, self.delay)
        reactor.callLater(self.delay, self.msgbus.connect)

    def handleConnLost(self):
        """Called to handle connection lost event

        """
        self.logger.warn('Connection of %s lost, retry %s later',
                         self.msgbus, self.delay)
        reactor.callLater(self.delay, self.msgbus.connect)


class HealthSupervisor(object):

    """This supervisor send message in message bus to check is the message bus
    still healthy

    """

    def __init__(self, msgbus, check_period=10, timeout=30, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.check_period = check_period
        self.timeout = timeout
        self.msgbus = msgbus
        self.msgbus.auth_event.subscribe(self.handleAuth)
        self.uid = uuid.uuid4().hex

        self._timeout_call = None
        self._send_call = None

    def handleAuth(self):
        """Called to handle authenticated event

        """
        self._dest = 'ping.' + self.uid
        self.msgbus.subscribe(self._dest, self.handleReply)
        self._cancel_timeout()
        self._cancel_send()
        self.sendPing()

    def handleReply(self, dest, data):
        if data != 'ping' and dest != self._dest:
            self.logger.warn('Wrong replay, dest=%r, data=%r, reconnect',
                             dest, data)
            self.msgbus.close()
            self.msgbus.connect()
        self._cancel_send()
        self._send_call = reactor.callLater(self.check_period, self.sendPing)

    def handleTimeout(self):
        self.logger.warn('Message bus timeout, reconnect')
        self._timeout_call = None
        self.msgbus.close()
        self.msgbus.connect()

    def _cancel_timeout(self):
        if self._timeout_call is not None:
            self._timeout_call.cancel()
            self._timeout_call = None

    def _cancel_send(self):
        if self._send_call is not None:
            self._send_call.cancel()
            self._send_call = None

    def sendPing(self):
        self._send_call = None
        self.msgbus.send(self._dest, 'ping')
        self._cancel_timeout()
        self._timeout_call = reactor.callLater(
            self.timeout, self.handleTimeout)
