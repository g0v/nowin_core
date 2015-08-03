import unittest

from nowin_core.utils.data_gen import DataGenerator


class MockTime(object):

    def __init__(self, now=0):
        self.now = now

    def __call__(self):
        return self.now


class TestDataGen(unittest.TestCase):

    def testGetData(self):
        time = MockTime()
        gen = DataGenerator(100, time)
        # make sure the first returned data is an empty string
        self.assertAlmostEqual(gen.getData(), '')

        kbit_bytes = 1000 * (1 / 8.0)

        time.now = 1
        data = gen.getData()
        self.assertAlmostEquals(len(data), 100 * kbit_bytes)

        time.now = 3
        data = gen.getData()
        self.assertAlmostEquals(len(data), 2 * 100 * kbit_bytes)

        time = MockTime()
        gen = DataGenerator(200, time)
        # make sure the first returned data is an empty string
        self.assertAlmostEqual(gen.getData(), '')

        time.now = 1
        data = gen.getData()
        self.assertAlmostEquals(len(data), 200 * kbit_bytes)

        time.now = 3
        data = gen.getData()
        self.assertAlmostEquals(len(data), 2 * 200 * kbit_bytes)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDataGen))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
