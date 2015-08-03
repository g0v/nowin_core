import json
import logging
import socket

from nowin_core.stomp import protocol


class StompError(Exception):

    """Stomp error

    """


class Client(object):

    recv_size = 4096

    def __init__(self, host, port, SocketClass=None, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger('stomp.client')
        self.SocketClass = SocketClass
        if self.SocketClass is None:
            self.SocketClass = socket.socket
        self.host = host
        self.port = port
        self.parser = protocol.Parser()
        self.connected = False
        self.session_id = None
        self.socket = None
        self.callbacks = {}

    def checkError(self, frame):
        if frame.command == 'ERROR':
            message = frame.headers['message']
            raise StompError(message)

    def getFrame(self):
        frame = None
        while frame is None:
            data = self.socket.recv(self.recv_size)
            if not data:
                break
            self.parser.feed(data)
            frame = self.parser.getFrame()
        return frame

    def login(self, user, password):
        """Login to STOMP server

        """
        assert self.connected is False

        self.socket = self.SocketClass(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

        frame = protocol.Frame('CONNECT', dict(login=user, passcode=password))
        self.socket.send(frame.pack())

        reply = self.getFrame()
        # disconnected
        if reply is None:
            self.connected = False
            self.logger.info('Session %s closed by peer', self.session_id)
            return

        self.checkError(reply)
        if reply.command == 'CONNECTED':
            self.session_id = reply.headers['session']
            self.connected = True
            self.logger.info('Logged in as %s with session %s',
                             user, self.session_id)
        else:
            raise StompError('Unknown command')

    def subscribe(self, dest, callback):
        """Subscribe to message queue `dest` with `callback` function

        """
        assert self.connected is True
        frame = protocol.Frame('SUBSCRIBE', dict(destination=dest))
        self.socket.send(frame.pack())
        self.callbacks[dest] = callback
        self.logger.info('Session %s subscribed to %s', self.session_id, dest)

    def unsubscribe(self, dest):
        """Unsubscribe from message queue

        """
        assert self.connected is True
        frame = protocol.Frame('UNSUBSCRIBE', dict(destination=dest))
        self.socket.send(frame.pack())
        del self.callbacks[dest]
        self.logger.info(
            'Session %s unsubscribed to %s', self.session_id, dest)

    def send(self, dest, data):
        """Send data to message queue

        """
        assert self.connected is True
        data = json.dumps(data)
        frame = protocol.Frame('SEND', dict(destination=dest), data)
        self.socket.send(frame.pack())
        self.logger.info('Session %s send %d bytes data to %s',
                         self.session_id, len(data), dest)

    def close(self):
        """Close connection to server

        """
        assert self.connected is True
        frame = protocol.Frame('DISCONNECT')
        self.socket.send(frame.pack())
        self.socket.close()
        self.connected = False
        self.logger.info('Session %s closed', self.session_id)

    def run(self):
        """Run loop for checking messages and calling callbacks

        """
        assert self.connected is True
        frame = None
        while True:
            frame = self.getFrame()
            if frame is None:
                break
            if frame.command != 'MESSAGE':
                raise StompError('Unexpected command %s', frame.command)
            dest = frame.headers['destination']
            callback = self.callbacks[dest]
            callback(dest, json.loads(frame.body))
        self.connected = False
        self.logger.info('Session %s closed by peer', self.session_id)
