import unittest

from nowin_core.stomp import protocol


class TestFrame(unittest.TestCase):

    def test_pack(self):
        body = 'body of SEND'
        p = protocol.Frame(
            'SEND',
            dict(login='user_name', passcode='password'),
            body=body
        )
        result = p.pack()
        lines = result.split(p.newline)

        self.assertEqual(lines[0], 'SEND')
        self.assert_('login:user_name' in lines[1:3])
        self.assert_('passcode:password' in lines[1:3])
        self.assertEqual(lines[4], body + '\0')
        self.assertEqual(len(lines), 5)

    def test_null_body(self):
        body = 'This is a body which has null\0Second line\0Third line'
        p = protocol.Frame('TEST', body=body)
        result = p.pack()
        lines = result.split(p.newline)

        self.assertEqual(lines[0], 'TEST')

        i = lines.index('')
        headers = lines[1:i]

        self.assertEqual(headers, ['content-length:%d' % len(body)])

        resultBody = p.newline.join(lines[i + 1:])
        self.assertEqual(resultBody, body + '\0')


class TestParser(unittest.TestCase):

    def setUp(self):
        self.parser = protocol.Parser()

    def assertFrame(self, frame, command, headers, body):
        self.assertEqual(frame.command, command)
        self.assertEqual(frame.headers, headers)
        self.assertEqual(frame.body, body)

    def test_colon(self):
        # test ":" in header
        value = 'test:123'
        data = 'SEND\n' \
            'value:%s\n' \
            '\nThis is the body\0' % value
        self.parser.feed(data)
        frame = self.parser.getFrame()
        self.assertFrame(
            frame,
            'SEND',
            dict(value=value),
            'This is the body'
        )

        value = 'test:123:456'
        data = 'SEND\n' \
            'value:%s\n' \
            '\nThis is the body\0' % value
        self.parser.feed(data)
        frame = self.parser.getFrame()
        self.assertFrame(
            frame,
            'SEND',
            dict(value=value),
            'This is the body'
        )

        value = '::::'
        data = 'SEND\n' \
            'value:%s\n' \
            '\nThis is the body\0' % value
        self.parser.feed(data)
        frame = self.parser.getFrame()
        self.assertFrame(
            frame,
            'SEND',
            dict(value=value),
            'This is the body'
        )

    def test_feed(self):
        data = 'SEND\n' \
            'login: test\n' \
            'passcode: 123abc\n' \
            '\nThis is the body\0' \

        for size in range(1, len(data)):
            for j in range(0, len(data), size):
                self.assertEqual(self.parser.getFrame(), None)
                self.parser.feed(data[j:j + size])

            frame = self.parser.getFrame()
            self.assertFrame(
                frame,
                'SEND',
                dict(login='test', passcode='123abc'),
                'This is the body'
            )

    def test_multi_feed(self):
        data1 = 'ACK\n' \
            'header1: value1\n' \
            'header2: value2\n' \
            '\nThis is the body 1\0' \

        data2 = 'SEND\n' \
            'header3: value3\n' \
            'header4: value4\n' \
            '\nThis is the body 2\0' \

        self.parser.feed(data1)
        frame = self.parser.getFrame()
        self.assertEqual(frame.command, 'ACK')
        self.assertEqual(
            frame.headers, dict(header1='value1', header2='value2'))
        self.assertEqual(frame.body, 'This is the body 1')

        self.parser.feed(data2)
        frame = self.parser.getFrame()
        self.assertEqual(frame.command, 'SEND')
        self.assertEqual(
            frame.headers, dict(header3='value3', header4='value4'))
        self.assertEqual(frame.body, 'This is the body 2')

        self.parser.feed(data1 + data2)
        frame = self.parser.getFrame()
        self.assertEqual(frame.command, 'ACK')
        self.assertEqual(
            frame.headers, dict(header1='value1', header2='value2'))
        self.assertEqual(frame.body, 'This is the body 1')
        frame = self.parser.getFrame()
        self.assertEqual(frame.command, 'SEND')
        self.assertEqual(
            frame.headers, dict(header3='value3', header4='value4'))
        self.assertEqual(frame.body, 'This is the body 2')

    def test_binaryl(self):
        binary = '\0\1\2\3\4\5\6\7\8\9\1'
        data = 'SEND\n' \
            'key: value\n' \
            'content-length: %d\n' \
            '\n%s\0' % (len(binary), binary)
        self.parser.feed(data)
        frame = self.parser.getFrame()
        self.assertEqual(frame.command, 'SEND')
        self.assertEqual(
            frame.headers,
            {
                'key': 'value',
                'content-length': str(len(binary))
            }
        )
        self.assertEqual(frame.body, binary)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFrame))
    suite.addTest(unittest.makeSuite(TestParser))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
