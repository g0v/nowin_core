import struct
import unittest

from nowin_core.source import protocol_2_0 as protocol


class TestParser(unittest.TestCase):

    def testMakeFrameOfLongData(self):
        limit = 65535
        id = 32
        packed_id = struct.pack('B', id)
        part_a = 'a' * limit
        part_b = 'b' * limit
        part_c = 'c' * 100

        data = part_a + part_b + part_c
        frames = protocol.makeFrames(id, data)

        self.assertEqual(len(frames), 3)

        self.assertEqual(frames[0][0], packed_id)
        self.assertEqual(frames[0][4:], part_a)

        self.assertEqual(frames[1][0], packed_id)
        self.assertEqual(frames[1][4:], part_b)

        self.assertEqual(frames[2][0], packed_id)
        self.assertEqual(frames[2][4:], part_c)

    def testGetFrame(self):
        data = 'DATA'
        id = 123

        frames = protocol.makeFrames(id, data)
        self.assertEqual(len(frames), 1)

        parser = protocol.Parser()
        parser.feed(frames[0])
        parsed_id, parsed_data = parser.getFrame()

        self.assertEqual(parsed_id, id)
        self.assertEqual(parsed_data, data)

    def testMultiParts(self):
        parser = protocol.Parser()

        def feedPart(id, data, frame, size):
            parser.feed(frame[:size])
            self.assertEqual(parser.getFrame(), None)

            parser.feed(frame[size:])
            parsed_id, parsed_data = parser.getFrame()
            self.assertEqual(parsed_id, id)
            self.assertEqual(parsed_data, data)

        id = 123
        data = 'THIS_IS_DATA'
        frame = protocol.makeFrames(id, data)[0]
        for n in range(len(frame)):
            feedPart(id, data, frame, n)

        id = 32
        data = 'abc' * 100
        frame = protocol.makeFrames(id, data)[0]
        for n in range(len(frame)):
            feedPart(id, data, frame, n)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParser))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
