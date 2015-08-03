import unittest


class TestAudioModel(unittest.TestCase):

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
        from nowin_core.models.audio import AudioModel
        return AudioModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def test_create_audio(self):
        import transaction
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

        with transaction.manager:
            audio_id = 'test_audio01'
            model.create_audio(
                audio_id=audio_id,
                user_id=user_id,
                filename='test_audio01.mp3',
                create_method=model.CREATE_METHOD_SERVER_RECORD,
                read_permission=model.PERMISSION_PUBLIC,
                size=1234,
            )
        audio = model.get_audio_by_id(audio_id)
        self.assertEqual(audio.id, audio_id)
        self.assertEqual(audio.user_id, user_id)
        self.assertEqual(audio.filename, 'test_audio01.mp3')
        self.assertEqual(
            audio.create_method, model.CREATE_METHOD_SERVER_RECORD)
        self.assertEqual(audio.read_permission, model.PERMISSION_PUBLIC)
        self.assertEqual(audio.size, 1234)
        self.assertEqual(audio.listened, 0)

        with transaction.manager:
            audio_id = 'test_audio02'
            model.create_audio(
                audio_id=audio_id,
                user_id=user_id,
                filename='test_audio02.mp3',
                create_method=model.CREATE_METHOD_UPLOAD,
                read_permission=model.PERMISSION_PRIVATE,
                size=5566,
                title='title',
                brief='brief'
            )
        audio = model.get_audio_by_id(audio_id)
        self.assertEqual(audio.id, audio_id)
        self.assertEqual(audio.user_id, user_id)
        self.assertEqual(audio.filename, 'test_audio02.mp3')
        self.assertEqual(audio.create_method, model.CREATE_METHOD_UPLOAD)
        self.assertEqual(audio.read_permission, model.PERMISSION_PRIVATE)
        self.assertEqual(audio.size, 5566)
        self.assertEqual(audio.listened, 0)
        self.assertEqual(audio.title, 'title')
        self.assertEqual(audio.brief, 'brief')

        # test invalid create method
        with self.assertRaises(ValueError):
            model.create_audio(
                audio_id='bad_audio',
                user_id=user_id,
                filename='bad_audio.mp3',
                create_method=999,
                read_permission=model.PERMISSION_PUBLIC,
                size=1234,
            )

        # test invalid read permission
        with self.assertRaises(ValueError):
            model.create_audio(
                audio_id='bad_audio',
                user_id=user_id,
                filename='bad_audio.mp3',
                create_method=model.CREATE_METHOD_SERVER_RECORD,
                read_permission=999,
                size=1234,
            )

    def test_update_audio(self):
        import transaction
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

        with transaction.manager:
            audio_id = 'test_audio01'
            model.create_audio(
                audio_id=audio_id,
                user_id=user_id,
                filename='test_audio01.mp3',
                create_method=model.CREATE_METHOD_SERVER_RECORD,
                read_permission=model.PERMISSION_PUBLIC,
                size=1234,
                title='title',
                brief='brief',
            )

            model.update_audio(
                audio_id,
                filename='new_file.mp3',
                size=7788,
                read_permission=model.PERMISSION_PRIVATE,
                title='new title',
                brief='new brief',
            )
        audio = model.get_audio_by_id(audio_id)
        self.assertEqual(audio.filename, 'new_file.mp3')
        self.assertEqual(audio.size, 7788)
        self.assertEqual(audio.read_permission, model.PERMISSION_PRIVATE)
        self.assertEqual(audio.title, 'new title')
        self.assertEqual(audio.brief, 'new brief')

    def testget_space_usage(self):
        import transaction
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

        usage = model.get_space_usage(user_id)
        self.assertEqual(usage['used'], 0)

        audio_id = 'test_audio01'
        with transaction.manager:
            model.create_audio(
                audio_id=audio_id,
                user_id=user_id,
                filename='test_audio01.mp3',
                create_method=model.CREATE_METHOD_SERVER_RECORD,
                read_permission=model.PERMISSION_PUBLIC,
                size=1234,
            )

        usage = model.get_space_usage(user_id)
        self.assertEqual(usage['used'], 1234)

        audio_id = 'test_audio02'
        with transaction.manager:
            model.create_audio(
                audio_id=audio_id,
                user_id=user_id,
                filename='test_audio02.mp3',
                create_method=model.CREATE_METHOD_SERVER_RECORD,
                read_permission=model.PERMISSION_PUBLIC,
                size=5678,
            )

        usage = model.get_space_usage(user_id)
        self.assertEqual(usage['used'], 1234 + 5678)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAudioModel))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
