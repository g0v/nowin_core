import unittest

from nowin_core.database import tables
from nowin_core.tests.models._helper import create_session


class TestRadioModel(unittest.TestCase):

    def setUp(self):
        import datetime
        tables.set_now_func(datetime.datetime.utcnow)
        self.session = create_session()

    def tearDown(self):
        self.session.remove()

    def make_user(self, name):
        """Make broadcast and proxy server

        """
        user_model = self.make_user_model()
        user_id = user_model.create_user(name, name + '@now.in', '', '')
        user_model.activate_user(user_id, '', '')
        return user_id

    def make_one(self):
        from nowin_core.models.radio import RadioModel
        return RadioModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def make_booking_model(self):
        from nowin_core.models.booking import BookingModel
        return BookingModel(self.session)

    def make_broadcast(
        self,
        name,
        user_count=0,
        user_limit=0,
        resource_count=0,
        resource_limit=0,
        active=True,
        alive=True
    ):
        booking = self.make_booking_model()
        ports = dict(source=name)
        booking.update_server(
            server_name=name,
            revision='123',
            pid='7788',
            user_count=user_count,
            user_limit=user_limit,
            resource_count=resource_count,
            resource_limit=resource_limit,
            active=active,
            alive=alive,
            loading=55.66,
            inbound_rate=0,
            outbound_rate=0,
            ports=ports,
            state='online'
        )

    def make_proxy(
        self,
        name,
        user_count=0,
        user_limit=0,
        resource_count=0,
        resource_limit=0,
        active=True,
        alive=True
    ):
        proxy = tables.Proxy(
            name=name,
            revision='123',
            pid='7788',
            user_count=user_count,
            user_limit=user_limit,
            resource_count=resource_count,
            resource_limit=resource_limit,
            active=active,
            alive=alive,
            loading=55.66,
            inbound_rate=0,
            outbound_rate=0,
        )
        web = tables.Port(name='web', address=name)
        proxy.ports.append(web)
        self.session.add(proxy)
        self.session.add(web)
        return proxy

    def test_get_broadcast_address(self):
        # FIXME: need some refactory here
        return
        model = self.make_one()

        # loading of b2 is less than b1
        self.make_broadcast('b1', 1, 10, 1, 10)
        self.make_broadcast('b2', 1, 20, 1, 20)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, 'b2')
        # clean up
        self.session = create_session()

        # loading of b1 is less than b2
        self.make_broadcast('b1', 1, 20, 1, 20)
        self.make_broadcast('b2', 1, 10, 1, 10)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, 'b1')
        # clean up
        self.session = create_session()

        # all are full
        self.make_broadcast('b1', 20, 20, 20, 20)
        self.make_broadcast('b2', 10, 10, 10, 10)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, None)
        # clean up
        self.session = create_session()

        # should compare res rate first
        self.make_broadcast('b1', 10, 20, 5, 20)
        self.make_broadcast('b2', 5, 20, 10, 20)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, 'b1')
        # clean up
        self.session = create_session()

        # should compare res rate first
        self.make_broadcast('b1', 5, 20, 10, 20)
        self.make_broadcast('b2', 10, 20, 5, 20)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, 'b2')
        # clean up
        self.session = create_session()

        # limit is 0, it means unlimited
        self.make_broadcast('b1')
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, 'b1')
        # clean up
        self.session = create_session()

        # not alive server should not appear
        self.make_broadcast('b1', alive=False)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, None)
        # clean up
        self.session = create_session()

        # not active server should not appear
        self.make_broadcast('b1', active=False)
        self.session.commit()
        address = model.get_broadcast_address()
        self.assertEqual(address, None)
        # clean up
        self.session = create_session()

    def testget_proxy_address(self):
        # FIXME: need some refactory here
        return
        model = self.make_one()
        user_model = self.make_user_model()

        def setProxy(proxy, **kwargs):
            for key, value in kwargs.iteritems():
                setattr(proxy, key, value)
            self.session.add(proxy)
            self.session.commit()

        b1 = self.make_broadcast('b1', 1, 10, 1, 10)
        user_id = self.make_user('user')
        user = user_model.get_user_by_id(user_id)
        user.on_air = tables.OnAir(server_id=b1.server_id)
        self.session.commit()

        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, None)

        # single proxy
        proxy1 = self.make_proxy('proxy1')
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, 'proxy1')

        # user rate of proxy 1 is less than proxy 2
        setProxy(proxy1, user_count=1, user_limit=10)
        proxy2 = self.make_proxy('proxy2', user_count=2, user_limit=10)
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, 'proxy1')

        # user rate of proxy 2 is less than proxy 1
        setProxy(proxy1, user_count=2, user_limit=10)
        setProxy(proxy2, user_count=1, user_limit=10)
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, 'proxy2')

        # all are full
        setProxy(proxy1, user_count=10, user_limit=10)
        setProxy(proxy2, user_count=10, user_limit=10)
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, None)

        # not active
        setProxy(proxy1, activate=False)
        setProxy(proxy2, activate=False)
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, None)

        # not alive
        setProxy(proxy1, activate=True, alive=False)
        setProxy(proxy2, activate=True, alive=False)
        self.session.commit()
        address = model.get_proxy_address(user.user_id)
        self.assertEqual(address, None)

    def test_get_sites(self):
        # FIXME: need some refactory here
        return
        model = self.make_one()

        b1 = self.make_broadcast('b1', 1, 10, 1, 10)
        u1 = self.make_user('u1')
        u1.on_air = tables.OnAir(server_id=b1.server_id)
        u2 = self.make_user('u2')
        u2.on_air = tables.OnAir(server_id=b1.server_id)
        p1 = self.make_proxy('p1')
        p2 = self.make_proxy('p2')
        self.session.flush()
        pc1 = tables.ProxyConnection(
            server_id=p1.id, user_id=u1.user_id, listener=10)
        pc2 = tables.ProxyConnection(
            server_id=p2.id, user_id=u1.user_id, listener=20)
        self.session.add(pc1)
        self.session.add(pc2)
        self.session.commit()

        sites = model.get_sites(order_by='listener_count')
        s1, l1 = sites[0]
        s2, l2 = sites[1]
        self.assertEquals(l1, 30)
        self.assertEquals(l2, 0)
        self.assertEqual(s1.user_id, u1.user_id)
        self.assertEqual(s2.user_id, u2.user_id)

        pc3 = tables.ProxyConnection(
            server_id=p1.id, user_id=u2.user_id, listener=50)
        pc4 = tables.ProxyConnection(
            server_id=p2.id, user_id=u2.user_id, listener=100)
        self.session.add(pc3)
        self.session.add(pc4)
        self.session.commit()

        sites = model.get_sites(order_by='listener_count')
        s1, l1 = sites[0]
        s2, l2 = sites[1]
        self.assertEquals(l1, 150)
        self.assertEquals(l2, 30)
        self.assertEqual(s1.user_id, u2.user_id)
        self.assertEqual(s2.user_id, u1.user_id)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRadioModel))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
