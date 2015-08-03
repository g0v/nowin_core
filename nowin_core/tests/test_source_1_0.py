import unittest


class TestParser(unittest.TestCase):

    def make_one(self):
        from nowin_core.source import protocol_1_0 as protocol
        return protocol

    def test_large_data(self):
        protocol = self.make_one()

        def test_with_feed_size(size):
            # generate input data
            input_chunks = []
            for i in range(1000):
                input_chunks.append('%s' % i)
            input_data = ','.join(input_chunks)

            frames = list(protocol.makeFrames('audio', input_data))
            frame_data = ''.join(frames)

            parsed_frames = []
            parser = protocol.Parser()
            for i in range(0, len(frame_data), size):
                chunk = frame_data[i:i + size]
                parser.feed(chunk)
                frame = parser.getFrame()
                while frame is not None:
                    parsed_frames.append(frame)
                    frame = parser.getFrame()

            parsed_data_chunks = []
            for channel, frame_data in parsed_frames:
                self.assertEqual(channel, 'audio')
                parsed_data_chunks.append(frame_data)

            output_data = ''.join(parsed_data_chunks)
            self.assertEqual(output_data, input_data)

        test_with_feed_size(100)
        test_with_feed_size(255)
        test_with_feed_size(256)
        test_with_feed_size(512)
        test_with_feed_size(513)
        test_with_feed_size(1024)
        test_with_feed_size(4096)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParser))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
