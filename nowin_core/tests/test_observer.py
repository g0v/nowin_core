import unittest


class TestObserver(unittest.TestCase):

    def make_one(self):
        from nowin_core.patterns.observer import Subject
        return Subject()

    def test_subscribe(self):
        sub = self.make_one()

        result = []

        def func(*args, **kwargs):
            result.append((args, kwargs))

        sub.subscribe(func)
        sub(1, 2, 3, k1='a', k2='b')
        self.assertEqual(result, [((1, 2, 3), dict(k1='a', k2='b'))])

        del result[:]
        sub.subscribe(func)
        sub('test2')
        self.assertEqual(result, [(('test2', ), {})] * 2)

    def test_unsubscribe(self):
        sub = self.make_one()

        result_a = []

        def func_a(data):
            result_a.append(data)

        result_b = []

        def func_b(data):
            result_b.append(data)

        sid_a = sub.subscribe(func_a)
        sid_b = sub.subscribe(func_b)

        sub('data1')
        self.assertEqual(result_a, ['data1'])
        self.assertEqual(result_b, ['data1'])

        del result_a[:]
        del result_b[:]
        sid_a.unsubscribe()
        sub('data2')
        self.assertEqual(result_a, [])
        self.assertEqual(result_b, ['data2'])

        del result_a[:]
        del result_b[:]
        sid_b.unsubscribe()
        sub('data3')
        self.assertEqual(result_a, [])
        self.assertEqual(result_b, [])

        with self.assertRaises(AssertionError):
            sid_b.unsubscribe()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestObserver))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
