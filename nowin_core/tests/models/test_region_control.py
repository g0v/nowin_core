import unittest


class TestCountryLimit(unittest.TestCase):

    def setUp(self):
        import datetime
        from nowin_core.tests.models._helper import create_session
        from nowin_core.database import tables
        tables.set_now_func(datetime.datetime.utcnow)
        self.session = create_session(zope_transaction=True)

    def tearDown(self):
        from nowin_core import signals
        # clean all signals by reloading them
        reload(signals)
        self.session.remove()

    def make_one(self):
        from nowin_core.models.region_control import RegionControlModel
        return RegionControlModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def test_update_country_limit(self):
        import transaction

        # create user
        user_model = self.make_user_model()
        with transaction.manager:
            user_id = user_model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='test_password'
            )
            user_model.activate_user(user_id, '', 'TW')

        model = self.make_one()
        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_INCLUDE, ['TW'])

        include_or_exclude, codes = model.get_country_limit(user_id)
        self.assertEqual(include_or_exclude, model.COUNTRY_INCLUDE)
        self.assertEqual(codes, ['TW'])

        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_EXCLUDE,
                                       ['TW', 'JP'])

        include_or_exclude, codes = model.get_country_limit(user_id)
        self.assertEqual(include_or_exclude, model.COUNTRY_EXCLUDE)
        self.assertEqual(set(codes), set(['TW', 'JP']))

        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_INCLUDE,
                                       [])

        include_or_exclude, codes = model.get_country_limit(user_id)
        self.assertEqual(include_or_exclude, model.COUNTRY_INCLUDE)
        self.assertEqual(codes, [])

    def test_is_country_allowed(self):
        import transaction

        # create user
        user_model = self.make_user_model()
        with transaction.manager:
            user_id = user_model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='test_password'
            )
            user_model.activate_user(user_id, '', 'TW')

        model = self.make_one()

        # test exclude
        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_EXCLUDE,
                                       ['TW', 'JP'])
        self.assertEqual(model.is_country_allowed(user_id, 'TW'), False)
        self.assertEqual(model.is_country_allowed(user_id, 'CN'), True)

        # test include
        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_INCLUDE,
                                       ['TW'])
        self.assertEqual(model.is_country_allowed(user_id, 'TW'), True)
        self.assertEqual(model.is_country_allowed(user_id, 'CN'), False)

        # test all ow
        with transaction.manager:
            model.update_country_limit(user_id, model.COUNTRY_EXCLUDE,
                                       [])
        self.assertEqual(model.is_country_allowed(user_id, 'TW'), True)
        self.assertEqual(model.is_country_allowed(user_id, 'CN'), True)
        self.assertEqual(model.is_country_allowed(user_id, 'JP'), True)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCountryLimit))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
