import unittest


class TestChatroomModel(unittest.TestCase):

    def setUp(self):
        import datetime
        from nowin_core.database import tables
        from nowin_core.tests.models._helper import create_session
        tables.set_now_func(datetime.datetime.utcnow)
        self.session = create_session(zope_transaction=True)

    def tearDown(self):
        from nowin_core import signals
        # clean all signals by reloading them
        reload(signals)
        self.session.remove()

    def make_one(self):
        from nowin_core.models.chatroom import ChatroomModel
        return ChatroomModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def test_update_settings(self):
        import transaction
        from nowin_core import signals
        from nowin_core.models.chatroom import ChatroomModel
        model = self.make_one()
        user_model = self.make_user_model()

        with transaction.manager:
            user_id = user_model.create_user(
                user_name='tester',
                email='tester@now.in',
                display_name='tester',
                password='test_password'
            )
            user_model.activate_user(user_id, '', 'TW')

        calls = []

        def callback(user_id):
            calls.append(user_id)

        signals.chatroom_setting_changed.subscribe(callback)

        def update(acl):
            model.update_settings(user_id, acl)
            settings = model.get_settings(user_id)
            self.assertEqual(settings['acl'], acl)

        update(ChatroomModel.ACL_OPEN)
        update(ChatroomModel.ACL_MEMBER)
        update(ChatroomModel.ACL_CLOSED)

        self.assertEqual([user_id] * 3, calls)

    def test_block_list(self):
        import transaction
        from nowin_core.models.chatroom import DuplicateError, NotExistError, \
            SelfBlockError

        model = self.make_one()
        user_model = self.make_user_model()

        with transaction.manager:
            owner_id = user_model.create_user(
                user_name='owner',
                email='owner@now.in',
                display_name='owner',
                password='owner_password'
            )
            user_model.activate_user(owner_id, '', 'TW')

            guest1_id = user_model.create_user(
                user_name='guest1',
                email='guest1@now.in',
                display_name='guest1',
                password='guest1_password'
            )
            user_model.activate_user(guest1_id, '', 'TW')

            guest2_id = user_model.create_user(
                user_name='guest2',
                email='guest2@now.in',
                display_name='guest2',
                password='guest2_password'
            )
            user_model.activate_user(guest2_id, '', 'TW')

        blocking = model.get_blocking(owner_id, guest1_id)
        self.assertEqual(blocking, None)

        with transaction.manager:
            model.add_blocked_user(owner_id, guest1_id)
        blocking = model.get_blocking(owner_id, guest1_id)
        self.assertNotEqual(blocking, None)

        with transaction.manager:
            model.remove_blocked_user(owner_id, guest1_id)
        blocking = model.get_blocking(owner_id, guest1_id)
        self.assertEqual(blocking, None)

        with transaction.manager:
            model.add_blocked_user(owner_id, guest1_id)
        self.assertEqual([guest1_id], model.get_blocked_list(owner_id))
        with transaction.manager:
            model.add_blocked_user(owner_id, guest2_id)
        self.assertEqual(set([guest1_id, guest2_id]),
                         set(model.get_blocked_list(owner_id)))

        # block a non-existing user
        with self.assertRaises(NotExistError):
            model.add_blocked_user(owner_id, 12345)

        # duplicate add
        with self.assertRaises(DuplicateError):
            model.add_blocked_user(owner_id, guest1_id)

        # try to block the owner self, should fail
        with self.assertRaises(SelfBlockError):
            model.add_blocked_user(owner_id, owner_id)

    def test_check_permission(self):
        import transaction
        from nowin_core.models.chatroom import ChatroomModel
        model = self.make_one()
        user_model = self.make_user_model()

        with transaction.manager:
            owner_id = user_model.create_user(
                user_name='owner',
                email='owner@now.in',
                display_name='owner',
                password='owner_password'
            )
            user_model.activate_user(owner_id, '', 'TW')

            guest1_id = user_model.create_user(
                user_name='guest1',
                email='guest1@now.in',
                display_name='guest1',
                password='guest1_password'
            )
            user_model.activate_user(guest1_id, '', 'TW')

            guest2_id = user_model.create_user(
                user_name='guest2',
                email='guest2@now.in',
                display_name='guest2',
                password='guest2_password'
            )
            user_model.activate_user(guest2_id, '', 'TW')

        def assert_permission(owner_id, guest_id, expected):
            result = model.check_permission(owner_id, guest_id)
            self.assertEqual(result, expected)
        # test open ACL
        with transaction.manager:
            model.update_settings(owner_id, acl=ChatroomModel.ACL_OPEN)
        assert_permission(owner_id, guest1_id, True)
        assert_permission(owner_id, guest2_id, True)
        assert_permission(owner_id, None, True)
        # block guest2
        with transaction.manager:
            model.add_blocked_user(owner_id, guest2_id)
        assert_permission(owner_id, guest1_id, True)
        assert_permission(owner_id, guest2_id, False)
        assert_permission(owner_id, None, True)

        # test member ACL
        with transaction.manager:
            model.remove_blocked_user(owner_id, guest2_id)
            model.update_settings(owner_id, acl=ChatroomModel.ACL_MEMBER)
        assert_permission(owner_id, guest1_id, True)
        assert_permission(owner_id, guest2_id, True)
        assert_permission(owner_id, None, False)
        # block guest1
        with transaction.manager:
            model.add_blocked_user(owner_id, guest1_id)
        assert_permission(owner_id, guest1_id, False)
        assert_permission(owner_id, guest2_id, True)
        assert_permission(owner_id, None, False)

        # make sure not activated user can't join member-only room
        with transaction.manager:
            guest_id = user_model.create_user(
                user_name='not_activated',
                email='not_activated@now.in',
                display_name='not_activated',
                password='not_activatedpassword'
            )
        assert_permission(owner_id, guest_id, False)
        with transaction.manager:
            user_model.activate_user(guest_id, '', 'TW')
        assert_permission(owner_id, guest_id, True)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestChatroomModel))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
