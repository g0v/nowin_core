import unittest


class MockMsgBus(object):

    def __init__(self):
        self.send_calls = []
        self.sub_calls = []
        self.unsub_calls = []

    def send(self, dest, data):
        from twisted.internet import defer
        d = defer.Deferred()
        self.send_calls.append((dest, data, d))
        return d

    def subscribe(self, dest, callback):
        from twisted.internet import defer
        d = defer.Deferred()
        self.sub_calls.append((dest, callback, d))
        return d

    def unsubscribe(self, id):
        from twisted.internet import defer
        d = defer.Deferred()
        self.unsub_calls.append((id, d))
        return d


class MockCallID(object):

    def __init__(self, seconds, func, args, kwargs):
        self.seconds = seconds
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.canceled = False
        self.called = False

    def call(self):
        self.called = True
        self.func(*self.args, **self.kwargs)

    def cancel(self):
        assert not self.called, 'already called'
        assert not self.canceled, 'already canceled'
        self.canceled = True


class MockReactor(object):

    def __init__(self):
        self.call_laters = []

    def callLater(self, seconds, func, *args, **kwargs):
        callid = MockCallID(seconds, func, args, kwargs)
        self.call_laters.append(callid)
        return callid


class TestRemoteCall(unittest.TestCase):

    def _makeOne(self, msgbus, dest, data, timeout=5, reactor=None):
        from nowin_core.message_bus.rpc import RemoteCall
        return RemoteCall(msgbus, dest, data, timeout, reactor=reactor)

    def test_reply_dest_check(self):
        msgbus = MockMsgBus()
        msg = dict(reply_dest='should not set this')
        test_dest = 'test_dest'
        with self.assertRaises(AssertionError):
            self._makeOne(msgbus, test_dest, msg)

    def test_already_called_check(self):
        msgbus = MockMsgBus()
        msg = dict()
        test_dest = 'test_dest'
        call = self._makeOne(msgbus, test_dest, msg)
        call()
        with self.assertRaises(AssertionError):
            call()

    def test_send_msg(self):
        msgbus = MockMsgBus()
        msg = dict(body='hello')
        test_dest = 'test_dest'
        call = self._makeOne(msgbus, test_dest, msg)
        call()

        _, _, deferred = msgbus.sub_calls[0]
        deferred.callback('subid')

        dest, data, _ = msgbus.send_calls[0]
        self.assertIn('reply_dest', data)
        self.assertEquals(dest, test_dest)

    def test_send_msg_failed(self):
        msgbus = MockMsgBus()
        msg = dict(body='hello')
        test_dest = 'test_dest'
        call = self._makeOne(msgbus, test_dest, msg)
        d = call()
        errbacks = []

        def on_error(error):
            errbacks.append(error)

        d.addErrback(on_error)

        _, _, deferred = msgbus.sub_calls[0]
        deferred.callback('subid')

        _, _, send_deferred = msgbus.send_calls[0]
        error = Exception('Boom')
        send_deferred.errback(error)

        self.assertEquals(len(errbacks), 1)
        self.assertEqual(errbacks[0].value, error)

    def test_remote_call(self):
        msgbus = MockMsgBus()
        msg = dict(body='hello')
        test_dest = 'test_dest'

        # make a remote call
        call = self._makeOne(msgbus, test_dest, msg)
        d = call()

        # handle the replies
        replies = []

        def on_replied(data):
            replies.append(data)

        d.addCallback(on_replied)

        _, _, deferred = msgbus.sub_calls[0]
        deferred.callback('subid')

        # send reply in message bus
        _, data, _ = msgbus.send_calls[0]
        reply_dest = data['reply_dest']
        _, callback, _ = msgbus.sub_calls[0]
        callback(reply_dest, dict(body='reply'))

        self.assertEqual(dict(body='reply'), replies[0])

    def test_timeout(self):
        msgbus = MockMsgBus()
        reactor = MockReactor()
        msg = dict(body='hello')
        test_dest = 'test_dest'

        # make a remote call
        call = self._makeOne(msgbus, test_dest, msg, reactor=reactor)
        d = call()
        errbacks = []

        def on_error(error):
            errbacks.append(error)

        d.addErrback(on_error)

        _, _, deferred = msgbus.sub_calls[0]
        deferred.callback('subid')

        # trigger the timeout callback
        callid = reactor.call_laters[0]
        callid.call()

        from nowin_core.message_bus.rpc import TimeoutError
        self.assertEquals(len(errbacks), 1)
        self.assertEqual(errbacks[0].value .__class__, TimeoutError)

    def test_already_canceled(self):
        from nowin_core.message_bus.rpc import CanceledError

        msgbus = MockMsgBus()
        reactor = MockReactor()

        msg = dict(body='hello')
        test_dest = 'test_dest'
        # make a remote call
        call = self._makeOne(msgbus, test_dest, msg, reactor=reactor)
        d = call()

        results = []

        def on_call(result):
            results.append(result)

        d.addBoth(on_call)
        call.cancel()

        _, _, deferred = msgbus.sub_calls[0]
        deferred.callback('subid')
        _, data, _ = msgbus.send_calls[0]
        reply_dest = data['reply_dest']
        _, callback, _ = msgbus.sub_calls[0]
        callback(reply_dest, dict(body='reply'))

        self.assertEqual(results[0].type, CanceledError)
        self.assertEqual(len(results), 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRemoteCall))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
