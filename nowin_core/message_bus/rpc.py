import logging
import uuid

from twisted.internet import defer


class TimeoutError(Exception):

    """Raised when remote call timeout

    """


class CanceledError(Exception):

    """Raised when remote call is canceled

    """


class RemoteCall(object):

    """A remote call in message bus

    """

    def __init__(
        self,
        msgbus,
        dest,
        data,
        timeout=5,
        prefix='rpc_reply.',
        reactor=None,
        logger=None
    ):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.reactor = reactor
        if self.reactor is None:
            from twisted.internet import reactor
            self.reactor = reactor
        assert 'reply_dest' not in data, 'reply_dest should not be in data'
        #: message bus to use
        self.msgbus = msgbus
        #: dest of remote function
        self.dest = dest
        #: data to send
        self.data = data
        #: how many seconds until timeout
        self.timeout = timeout
        #: prefix of replying address
        self.prefix = prefix
        #: is this remote call already called?
        self.called = False
        #: is this remote call already canceled?
        self.canceled = False
        #: is this remote call replied?
        self.replied = False
        #: unique id of this call
        self.uuid = uuid.uuid4().hex
        #: subscribe id
        self._sub_id = None
        #: call id for timeout
        self._call_id = None
        #: deferred object for returning result and error
        self.deferred = defer.Deferred()

    def __call__(self):
        assert not self.called, 'already called'
        self.called = True
        reply_dest = self.prefix + self.uuid
        self.logger.info('Remotely calling to %s, reply_dest=%s ...',
                         self.dest, reply_dest)
        self.data['reply_dest'] = reply_dest

        def sub_callback(id):
            self._sub_id = id
            d = self.msgbus.send(self.dest, self.data)
            d.addErrback(self._handleError)
            self._call_id = self.reactor.callLater(self.timeout,
                                                   self._handleTimeout)
            return id
        d = self.msgbus.subscribe(reply_dest, self._handleResult)
        d.addCallback(sub_callback)
        d.addErrback(self._handleError)
        return self.deferred

    def cancel(self):
        """Cancel the remote call

        """
        if self.canceled or self.replied:
            return
        self.canceled = True
        self._clear()
        self.deferred.errback(CanceledError('canceled by user'))
        self.logger.info('Cancel remote call to %s', self.dest)

    def _clear(self):
        """Clear up

        """
        if self._call_id is not None:
            self._call_id.cancel()
        if self._sub_id is not None:
            self.msgbus.unsubscribe(self._sub_id)

    def _handleError(self, error):
        """Called to handle error

        """
        self.logger.error('Failed to call to %s with error %s',
                          self.dest, error)
        self.deferred.errback(error)
        self._clear()

    def _handleTimeout(self):
        """Called to handle timeout

        """
        self.logger.error('Failed to call to %s, timeout', self.dest)
        self.deferred.errback(TimeoutError('timeout'))
        self._call_id = None
        self._clear()

    def _handleResult(self, dest, data):
        """Called to handle result

        """
        if self.canceled:
            self.logger.info('RPC canceled')
            return
        self.logger.info('Received reply to %s', dest)
        self.replied = True
        self.deferred.callback(data)
        self._clear()
