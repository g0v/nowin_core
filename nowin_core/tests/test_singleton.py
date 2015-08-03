import unittest


class TestSingleton(unittest.TestCase):

    def test_only_one_instance(self):
        from nowin_core.patterns.singleton import singleton

        created = []

        @singleton
        class MockObj(object):

            def __init__(self):
                created.append(self)

        # make sure the object was created correctly
        obj = MockObj()
        self.assertEqual(1, len(created))
        self.assertEqual(obj, created[0])

        # make sure only one object will be created
        new_obj = MockObj()
        self.assertEqual(id(obj), id(new_obj))
        self.assertEqual(1, len(created))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSingleton))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
