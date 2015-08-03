import unittest

from nowin_core.utils.bandwidth import Bandwidth


class MockTime(object):

    def __init__(self, now=0):
        self.now = now

    def __call__(self):
        return self.now


class TestBandwidth(unittest.TestCase):

    def testRate(self):
        time = MockTime()
        band = Bandwidth(time)
        # make sure first calculate should not generate error
        band.calculate()
        self.assertEqual(band.byte_rate, 0)

        band.increase(80)
        time.now = 2
        band.calculate()
        # 80/2 should be 40 Bps
        self.assertAlmostEqual(band.byte_rate, 40)

        bytes = 1000000
        time.now = 3
        band.increase(bytes)
        band.calculate()
        bits = bytes * 8
        mbps = bits / 1000000.0
        self.assertAlmostEqual(band.mbps, mbps)

    def testEvent(self):
        result = []

        def callback(rate):
            result.append(rate)

        time = MockTime()
        band = Bandwidth(time)
        band.update_event.subscribe(callback)
        # rate should be 0
        band.calculate()

        band.increase(20)
        time.now = 2
        # rate should be 10
        band.calculate()

        self.assertAlmostEqual(result[0], 0)
        self.assertAlmostEqual(result[1], 10)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBandwidth))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
