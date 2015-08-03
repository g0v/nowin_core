import unittest

from nowin_core.memory import audio_stream


class TestAudioStream(unittest.TestCase):

    def testWrite(self):
        audioStream = audio_stream.AudioStream(3, 5)
        data = '1234567890'
        audioStream.write(data)
        # the buffer should be 123456789xxxxxxxxxxxxxxxxxxxxx now
        # because the block size is 3, so that 0 is not in the buffer
        self.assertEqual(audioStream.base, 0)
        self.assertEqual(audioStream.middle, 3)
        self.assertEqual(audioStream.buffer[:9], data[:9])
        audioStream.write('ab')
        self.assertEqual(audioStream.buffer[:12], '1234567890ab')
        audioStream.write('a')
        audioStream.write('s')
        audioStream.write('d')
        audioStream.write('f')
        # f is in piece buffer
        self.assertEqual(audioStream.base, 0)
        self.assertEqual(audioStream.middle, 6)
        self.assertEqual(audioStream.buffer, '1234567890abasd')
        audioStream.write('uc')
        audioStream.write('k')
        # k is in piece buffer

        #     3 <- base
        #             9 <- middle
        # 123 456 789 0ab asd fuc k
        self.assertEqual(audioStream.base, 3)
        self.assertEqual(audioStream.middle, 9)
        self.assertEqual(audioStream.buffer, 'fuc4567890abasd')
        audioStream.write('you')
        # u is in piece buffer
        self.assertEqual(audioStream.buffer, 'fuckyo7890abasd')
        audioStream.write('justkidding')
        self.assertEqual(audioStream.buffer, 'ingkyoujustkidd')

    def testRead(self):
        audioStream = audio_stream.AudioStream(3, 5)
        audioStream.write('1234567890ab')
        offset = 0

        block, offset = audioStream.read(offset)
        self.assertEqual(block, '123')
        self.assertEqual(offset, 3)

        block, offset = audioStream.read(offset)
        self.assertEqual(block, '456')
        self.assertEqual(offset, 6)

        block, offset = audioStream.read(offset)
        self.assertEqual(block, '789')
        self.assertEqual(offset, 9)

        block, offset = audioStream.read(offset)
        self.assertEqual(block, '0ab')
        self.assertEqual(offset, 12)
        # there is no new data
        block, offset = audioStream.read(offset)
        self.assertEqual(block, None)
        self.assertEqual(offset, 12)

        audioStream.write('cde')
        block, offset = audioStream.read(offset)
        self.assertEqual(block, 'cde')
        self.assertEqual(offset, 15)

        audioStream.write('fghijk')
        block, offset = audioStream.read(offset)
        self.assertEqual(block, 'fgh')
        self.assertEqual(offset, 18)
        block, offset = audioStream.read(offset)
        self.assertEqual(block, 'ijk')
        self.assertEqual(offset, 21)

        # out of window, should be in the middle of buffer
        #    9   12  15
        # 789 0ab cde cfg ijk
        block, offset = audioStream.read(0)
        self.assertEqual(audioStream.middle, 12)
        self.assertEqual(block, 'cde')
        self.assertEqual(offset, 15)

        block, offset = audioStream.read(3)
        self.assertEqual(block, 'cde')
        self.assertEqual(offset, 15)

        audioStream.write('012345')

        # out of buffer, should be in the middle of buffer
        #    15  18  21  24
        # cde cfg ijk 012 345
        block, offset = audioStream.read(0)
        self.assertEqual(audioStream.middle, 18)
        self.assertEqual(block, 'ijk')
        self.assertEqual(offset, 21)

        block, offset = audioStream.read(3)
        self.assertEqual(block, 'ijk')
        self.assertEqual(offset, 21)

        block, offset = audioStream.read(6)
        self.assertEqual(block, 'ijk')
        self.assertEqual(offset, 21)

        block, offset = audioStream.read(9)
        self.assertEqual(block, 'ijk')
        self.assertEqual(offset, 21)

    def testGetData(self):
        stream = audio_stream.AudioStream(3, 5)
        stream.write('1')
        self.assertEqual(stream.data, '1')
        stream.write('2')
        self.assertEqual(stream.data, '12')
        stream.write('3')
        self.assertEqual(stream.data, '123')
        stream.write('4567')
        self.assertEqual(stream.data, '1234567')
        stream.write('89abcde')
        self.assertEqual(stream.data, '123456789abcde')
        stream.write('f')
        self.assertEqual(stream.data, '123456789abcdef')
        stream.write('g')
        self.assertEqual(stream.data, '123456789abcdefg')
        stream.write('hijk')
        self.assertEqual(stream.data, '456789abcdefghijk')
        stream.write('123456789abcdef')
        self.assertEqual(stream.data, 'jk123456789abcdef')
        stream.write('123456789')
        self.assertEqual(stream.data, '89abcdef123456789')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAudioStream))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
