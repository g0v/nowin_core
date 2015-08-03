import json
import logging
import os

import txamqp.spec
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.internet.protocol import ClientCreator
from txamqp.client import TwistedDelegate
from txamqp.content import Content
from txamqp.protocol import AMQClient


class AMQPMessageBus(object):

    def __init__(
        self,
        hosts,
        exchange_name='message_bus',
        vhost='/',
        spec_path=os.path.join('specs', 'standard', 'amqp0-8.xml'),
        logger=None
    ):
        """

        """
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        self.hosts = hosts
        self.vhost = vhost
        self.exchange_name = exchange_name
        self.conn = None
        # map tab to queue name
        self.queues = {}

        path = os.path.join(os.path.dirname(__file__), spec_path)
        self.spec = txamqp.spec.load(path)
        self.logger.debug('Load sepc %s', path)

        self.logger.info('Create message bus with hosts %s', self.hosts)

    @inlineCallbacks
    def login(self, user, password):
        """Login message bus

        """
        self.logger.debug('Logging in as %s ...', user)
        host = self.hosts[0]

        delegate = TwistedDelegate()
        creactor = ClientCreator(reactor, AMQClient, delegate=delegate,
                                 vhost=self.vhost, spec=self.spec)

        self.conn = yield creactor.connectTCP(host[0], host[1])
        yield self.conn.authenticate(user, password)
        self.channel = yield self.conn.channel(1)
        yield self.channel.channel_open()
        yield self.channel.exchange_declare(exchange=self.exchange_name,
                                            type='topic')
        self.logger.info('Login as %s', user)

    @inlineCallbacks
    def send(self, dest, data):
        """Send data to message bus

        """
        dest = str(dest)
        data = json.dumps(data)
        self.logger.debug('Sending %s bytes to %s ...', len(data), dest)
        yield self.channel.basic_publish(exchange=self.exchange_name,
                                         routing_key=dest,
                                         content=Content(data))
        self.logger.info('Sent %s bytes to %s', len(data), dest)

    @inlineCallbacks
    def _poll_queue(self, queue_tag, callback):
        self.logger.debug('Polling queue %s to %s', queue_tag, callback)
        queue = yield self.conn.queue(queue_tag)
        while True:
            try:
                msg = yield queue.get()
            except txamqp.queue.Closed:
                self.logger.debug('Stop polling queue %s ', queue_tag)
                break
            data = json.loads(msg.content.body)
            callback(msg.routing_key, data)

    @inlineCallbacks
    def subscribe(self, dest, callback):
        """Subscribe to specific destination, the callback will be called when
        the there is message in the destination

        """
        dest = str(dest)
        self.logger.debug('Subscribing to %s ...', dest)
        result = yield self.channel.queue_declare(
            exclusive=True,
            durable=False,
        )
        queue_name = result.queue
        yield self.channel.queue_bind(exchange=self.exchange_name,
                                      queue=queue_name,
                                      routing_key=dest)

        result = yield self.channel.basic_consume(
            queue=queue_name,
            no_ack=True,
        )
        queue_tag = result.consumer_tag
        self.queues[queue_tag] = queue_name
        self._poll_queue(queue_tag, callback)
        self.logger.info('Subscribed to %s with id %r', dest, queue_tag)
        returnValue(queue_tag)

    @inlineCallbacks
    def unsubscribe(self, id):
        """Unsubscribe from message bus

        """
        queue_name = self.queues[id]
        self.logger.debug('Unsubscribe... from queue %s with id %s',
                          queue_name, id)
        yield self.channel.basic_cancel(id)
        yield self.channel.queue_delete(queue=queue_name)
        del self.queues[id]
        queue = yield self.conn.queue(id)
        queue.close()
        self.logger.info('Unsubscribed from queue %s with id %s',
                         queue_name, id)

    @inlineCallbacks
    def close(self):
        """Close connection to message bus

        """
        self.logger.debug('Closing message bus ...')
        yield self.conn.close('Closed by user')
        self.logger.info('Closed message bus')
