import unittest


class TestUserModel(unittest.TestCase):

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
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def make_group_model(self):
        from nowin_core.models.group import GroupModel
        return GroupModel(self.session)

    def test_create_user(self):
        import transaction
        from nowin_core import signals
        model = self.make_one()

        user_name = 'victorlin'
        email = 'bornstub@gmail.com'
        display_name = user_name
        password = 'thepass'

        result = []

        def callee(user_id):
            result.append(user_id)

        signals.user_created_event.subscribe(callee)

        with transaction.manager:
            user_id = model.create_user(
                user_name=user_name,
                email=email,
                display_name=display_name,
                password=password
            )
        user = model.get_user_by_id(user_id)
        verification = model.get_verification(user_id, 'create_user')

        # make sure the signal was called
        self.assertEqual(result, [user_id])

        self.assertEqual(user.user_name, user_name)
        self.assertEqual(user.email, email)
        self.assertEqual(user.display_name, display_name)

        # make sure the password is not in plain form
        self.assertNotEqual(user.password, password)

        # make sure the user is not active
        self.assertEqual(user.active, False)

        self.assertEqual(verification.user, user)
        self.assertEqual(verification.type, u'create_user')

        # ## activate user ###
        result = []
        signals.user_activated_event.subscribe(callee)
        with transaction.manager:
            model.activate_user(user_id, u'title', u'location')

        # make sure the signal was called
        self.assertEqual(result, [user_id])

        user = model.get_user_by_id(user_id)
        site = user.site
        self.assertNotEqual(user.site, None)
        self.assertEqual(site.title, u'title')
        self.assertEqual(site.location, u'location'.upper())
        self.assertEqual(user.active, True)

    def test_authenticate_user(self):
        import transaction
        model = self.make_one()

        with transaction.manager:
            user_1 = model.create_user(
                user_name=u'tester',
                email=u'tester@now.in',
                display_name=u'tester',
                password=u'first_pass'
            )
            model.activate_user(user_1, u'title', u'location')
            user_2 = model.create_user(
                user_name=u'tester2',
                email=u'tester2@now.in',
                display_name=u'tester2',
                password=u'pass2'
            )
            model.activate_user(user_2, u'title', u'location')
            user_3 = model.create_user(
                user_name=u'tester3',
                email=u'tester3@now.in',
                display_name=u'tester2',
                password=u'tester3_PaSs3'
            )
            model.activate_user(user_3, u'title', u'location')

        # cases should pass
        result = model.authenticate_user(u'tester', u'first_pass')
        self.assertEqual(result, user_1)
        result = model.authenticate_user(u'tester@now.in', u'first_pass')
        self.assertEqual(result, user_1)

        result = model.authenticate_user(u'tester2', u'pass2')
        self.assertEqual(result, user_2)
        result = model.authenticate_user(u'TeStEr2', u'pass2')
        self.assertEqual(result, user_2)
        result = model.authenticate_user(u'tester2@now.in', u'pass2')
        self.assertEqual(result, user_2)
        result = model.authenticate_user(u'TESTER2@now.in', u'pass2')
        self.assertEqual(result, user_2)
        result = model.authenticate_user(u'TeSTer2@now.in', u'pass2')
        self.assertEqual(result, user_2)

        result = model.authenticate_user(u'tester3', u'tester3_PaSs3')
        self.assertEqual(result, user_3)
        result = model.authenticate_user(u'tester3@now.in', u'tester3_PaSs3')
        self.assertEqual(result, user_3)

        # cases should not pass
        from nowin_core.models.user import BadPassword
        from nowin_core.models.user import UserNotExist
        from nowin_core.models.user import UserNotActived

        with self.assertRaises(BadPassword):
            model.authenticate_user(u'tester@now.in', u'First_pass')
        with self.assertRaises(BadPassword):
            model.authenticate_user(u'tester@now.in', u'First_Pass')
        with self.assertRaises(BadPassword):
            model.authenticate_user(u'tester@now.in', u'abcd')
        with self.assertRaises(BadPassword):
            model.authenticate_user(u'tester@now.in', u'')
        with self.assertRaises(BadPassword):
            model.authenticate_user(u'tester2@now.in', u'abc')
        with self.assertRaises(UserNotExist):
            model.authenticate_user(u'user_not_exist', u'abc')

        # make sure not activated user can't not login
        with transaction.manager:
            model.create_user(
                user_name=u'not_activated',
                email=u'not_activated@now.in',
                display_name=u'not_activated',
                password=u'not_activated'
            )
        with self.assertRaises(UserNotActived):
            model.authenticate_user(u'not_activated', 'not_activated')

    def test_update_site(self):
        import transaction
        model = self.make_one()
        with transaction.manager:
            user_id = model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='abc'
            )
            model.activate_user(user_id, u'title', u'location')
            model.update_site(
                user_id,
                title='tester radio',
                brief='tester brief',
                description='tester description',
                tags=['a', 'b', 'c'],
                location='TW',
                image_name='my_image',
                public=True
            )
        user = model.get_user_by_id(user_id)
        site = user.site
        self.assertEqual(site.title, 'tester radio')
        self.assertEqual(site.brief, 'tester brief')
        self.assertEqual(site.description, 'tester description')
        self.assertEqual(site.location, 'TW')
        self.assertEqual(site.image_name, 'my_image')
        self.assertEqual(site.public, True)
        tags = set([tag.name for tag in site.tags])
        self.assertEqual(tags, set(['a', 'b', 'c']))

        with transaction.manager:
            model.update_site(
                user_id,
                title='title',
                brief='brief',
                description='description',
                tags=['a', 'b'],
                location='US',
                image_name='my_image2',
                public=False
            )
        user = model.get_user_by_id(user_id)
        site = user.site
        self.assertEqual(site.title, 'title')
        self.assertEqual(site.brief, 'brief')
        self.assertEqual(site.description, 'description')
        self.assertEqual(site.location, 'US')
        self.assertEqual(site.image_name, 'my_image2')
        self.assertEqual(site.public, False)
        tags = set([tag.name for tag in site.tags])
        self.assertEqual(tags, set(['a', 'b']))

        with transaction.manager:
            model.update_site(
                user.user_id,
                public=True
            )
        user = model.get_user_by_id(user_id)
        site = user.site
        self.assertEqual(site.title, 'title')
        self.assertEqual(site.brief, 'brief')
        self.assertEqual(site.description, 'description')
        self.assertEqual(site.location, 'US')
        self.assertEqual(site.image_name, 'my_image2')
        self.assertEqual(site.public, True)
        tags = set([tag.name for tag in site.tags])
        self.assertEqual(tags, set(['a', 'b']))

        with transaction.manager:
            model.update_site(
                user.user_id,
                image_name='my_image3'
            )
        user = model.get_user_by_id(user_id)
        site = user.site
        self.assertEqual(site.title, 'title')
        self.assertEqual(site.brief, 'brief')
        self.assertEqual(site.description, 'description')
        self.assertEqual(site.location, 'US')
        self.assertEqual(site.image_name, 'my_image3')
        self.assertEqual(site.public, True)
        tags = set([tag.name for tag in site.tags])
        self.assertEqual(tags, set(['a', 'b']))

        def update_tags(tags):
            with transaction.manager:
                model.update_site(
                    user_id,
                    tags=tags,
                )
            user = model.get_user_by_id(user_id)
            site = user.site
            self.assertEqual(set([tag.name for tag in site.tags]), set(tags))

        update_tags(['1', '2'])
        update_tags(['1'])
        update_tags([])
        update_tags(['def'])
        update_tags(['123', '456'])

    def test_update_profile(self):
        import transaction
        model = self.make_one()
        with transaction.manager:
            user_id = model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='abc'
            )
            model.activate_user(user_id, u'title', u'location')

        with transaction.manager:
            model.update_profile(user_id, profile='this is profile of tester')
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.profile, 'this is profile of tester')

        with transaction.manager:
            model.update_profile(user_id, display_name='new name')
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.display_name, 'new name')

        import datetime
        birthday = datetime.date.today()
        with transaction.manager:
            model.update_profile(user_id, birthday=birthday)
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.birthday, birthday)

        with transaction.manager:
            model.update_profile(user_id, gender=model.GENDER_FEMALE)
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.gender, model.GENDER_FEMALE)

        with transaction.manager:
            model.update_profile(user_id, website_link='http://facebook.com')
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.website_link, 'http://facebook.com')

    def test_update_user_enable(self):
        import transaction
        model = self.make_one()
        with transaction.manager:
            user_id = model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='abc'
            )
            model.activate_user(user_id, u'title', u'location')

        user = model.get_user_by_id(user_id)
        self.assertEqual(user.enable, True)

        with transaction.manager:
            model.update_user_enable(user_id, False)
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.enable, False)
        users = list(model.get_users_by_enable(False))
        self.assertEqual(users, [user])
        users = list(model.get_users_by_enable(True))
        self.assertEqual(len(users), 0)

        with transaction.manager:
            model.update_user_enable(user_id, True)
        user = model.get_user_by_id(user_id)
        self.assertEqual(user.enable, True)
        users = list(model.get_users_by_enable(True))
        self.assertEqual(users, [user])
        users = list(model.get_users_by_enable(False))
        self.assertEqual(len(users), 0)

    def test_update_groups(self):
        import transaction
        model = self.make_one()
        group_model = self.make_group_model()

        user_name = 'victorlin'
        email = 'bornstub@gmail.com'
        display_name = user_name
        password = 'thepass'

        with transaction.manager:
            user_id = model.create_user(
                user_name=user_name,
                email=email,
                display_name=display_name,
                password=password,
            )
            gid1 = group_model.create_group('g1')
            gid2 = group_model.create_group('g2')
            gid3 = group_model.create_group('g3')

        user = model.get_user_by_id(user_id)
        gids = set([g.group_id for g in user.groups])
        self.assertEqual(gids, set([]))

        def assert_update(new_groups):
            with transaction.manager:
                model.update_groups(user_id, new_groups)
            user = model.get_user_by_id(user_id)
            gids = set([g.group_id for g in user.groups])
            self.assertEqual(gids, set(new_groups))

        assert_update([gid1])
        assert_update([gid1, gid2])
        assert_update([gid1, gid2, gid3])
        assert_update([gid1, gid3])
        assert_update([gid3])
        assert_update([])


class TestFollowingModel(unittest.TestCase):

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
        from nowin_core.models.user import FollowingModel
        return FollowingModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def test_add_following(self):
        import transaction
        user_model = self.make_user_model()

        with transaction.manager:
            user_1 = user_model.create_user(
                user_name=u'tester',
                email=u'tester@now.in',
                display_name=u'tester',
                password=u'first_pass'
            )
            user_model.activate_user(user_1, u'title', u'location')

            user_2 = user_model.create_user(
                user_name=u'tester2',
                email=u'tester2@now.in',
                display_name=u'tester',
                password=u'first_pass'
            )
            user_model.activate_user(user_2, u'title', u'location')

        model = self.make_one()
        self.assertEqual(model.get_following_state(user_1, user_2), None)
        with transaction.manager:
            model.add_following(user_1, user_2)
        self.assertEqual(model.get_following_state(user_1, user_2), 1)
        self.assertEqual(model.get_following_state(user_2, user_1), 2)
        with transaction.manager:
            model.add_following(user_2, user_1)
        self.assertEqual(model.get_following_state(user_1, user_2), 3)
        self.assertEqual(model.get_following_state(user_2, user_1), 3)
        with transaction.manager:
            model.remove_following(user_1, user_2)
        self.assertEqual(model.get_following_state(user_1, user_2), 2)
        self.assertEqual(model.get_following_state(user_2, user_1), 1)


class TestPrivacyModel(unittest.TestCase):

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
        from nowin_core.models.user import PrivacyModel
        return PrivacyModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def test_set_options(self):
        import transaction
        user_model = self.make_user_model()

        with transaction.manager:
            user_id = user_model.create_user(
                user_name=u'tester',
                email=u'tester@now.in',
                display_name=u'tester',
                password=u'first_pass'
            )
            user_model.activate_user(user_id, u'title', u'location')

        model = self.make_one()
        options = dict(
            blood_type=model.OPTION_FIRENDS_ONLY,
            gender=model.OPTION_HIDDEN,
            birthday=model.OPTION_PUBLIC
        )
        with transaction.manager:
            model.set_options(user_id, **options)
        result = model.get_options(user_id)
        self.assertEqual(options, result)

        with transaction.manager:
            model.set_options(
                user_id,
                gender=model.OPTION_PUBLIC,
                new_op=model.OPTION_FIRENDS_ONLY
            )
        expected = options.copy()
        expected['gender'] = model.OPTION_PUBLIC
        expected['new_op'] = model.OPTION_FIRENDS_ONLY
        result = model.get_options(user_id)
        self.assertEqual(result, expected)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUserModel))
    suite.addTest(unittest.makeSuite(TestFollowingModel))
    suite.addTest(unittest.makeSuite(TestPrivacyModel))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
