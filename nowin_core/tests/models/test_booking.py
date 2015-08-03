import datetime
import unittest


class MockNow(object):

    def __init__(self, now=datetime.datetime.utcnow()):
        self.now = now

    def __call__(self):
        return self.now


class TestBookingModel(unittest.TestCase):

    def setUp(self):
        from nowin_core.database import tables
        from nowin_core.tests.models._helper import create_session
        self.session = create_session()
        self.now_func = MockNow()
        self.oldNowFunc = tables.set_now_func(self.now_func)

    def tearDown(self):
        from nowin_core.database import tables
        tables.set_now_func(self.oldNowFunc)
        self.session.remove()

    def make_one(self):
        from nowin_core.models.booking import BookingModel
        return BookingModel(self.session)

    def make_user_model(self):
        from nowin_core.models.user import UserModel
        return UserModel(self.session)

    def make_host(self, model):
        """Make a dummy host for testing and return

        """
        host_ip = '127.0.0.1'
        name = 'test_host'
        alive = False
        loading = 55.66
        supervisor_url = 'http://now.in'

        host = model.add_host(
            host_ip=host_ip,
            name=name,
            alive=alive,
            loading=loading,
            supervisor_url=supervisor_url
        )
        return host

    def create_users(self, count):
        # create some dummy users for testing
        user_model = self.make_user_model()
        user_ids = []
        for i in range(count):
            name = u'user%s' % i
            user_id = user_model.create_user(name, name + '@now.in', '', '')
            user_model.activate_user(user_id, name, u'TW')
            user_ids.append(user_id)
        return user_ids

    def test_now_func(self):
        from nowin_core.database import tables
        for _ in range(100):
            self.assertEqual(tables.now_func(), self.now_func.now)
        self.now_func.now += datetime.timedelta(seconds=99)
        self.assertEqual(tables.now_func(), self.now_func.now)
        self.now_func.now -= datetime.timedelta(seconds=888)
        self.assertEqual(tables.now_func(), self.now_func.now)

    def test_add_host(self):
        import transaction
        model = self.make_one()
        host_ip = '127.0.0.1'
        name = 'test_host'
        alive = True
        loading = 55.66
        supervisor_url = 'http://now.in'

        with transaction.manager:
            model.add_host(
                host_ip=host_ip,
                name=name,
                alive=alive,
                loading=loading,
                supervisor_url=supervisor_url
            )
        host = model.get_host_by_ip(host_ip)

        self.assertEqual(host.ip, host_ip)
        self.assertEqual(host.name, name)
        self.assertEqual(host.alive, alive)
        self.assertEqual(host.loading, loading)
        self.assertEqual(host.supervisor_url, supervisor_url)
        self.assertEqual(host.last_updated, self.now_func.now)

    def test_update_host(self):
        import transaction
        model = self.make_one()
        host_ip = '192.168.0.1'
        name = 'test_host_123'
        alive = False
        loading = 55.6677
        supervisor_url = 'http://now.in/supervisor'

        with transaction.manager:
            model.add_host(
                host_ip=host_ip,
                name=name,
                alive=alive,
                loading=loading,
                supervisor_url=supervisor_url
            )

        # test online state
        state = 'online'
        loading = 77.88
        supervisor_url = 'http://new-url.com'
        self.now_func.now += datetime.timedelta(seconds=10)
        with transaction.manager:
            model.update_host(host_ip, 'test', state, loading, supervisor_url)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, True)
        self.assertEqual(host.loading, loading)
        self.assertEqual(host.supervisor_url, supervisor_url)
        self.assertEqual(host.online_time, self.now_func.now)
        old_online_time = host.online_time

        # test normal
        state = 'normal'
        loading = 33.44
        supervisor_url = 'http://normal.com'
        self.now_func.now += datetime.timedelta(seconds=10)
        with transaction.manager:
            model.update_host(host_ip, 'test', state, loading, supervisor_url)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, True)
        self.assertEqual(host.loading, loading)
        self.assertEqual(host.supervisor_url, supervisor_url)
        self.assertEqual(host.online_time, old_online_time)

        # test offline state
        state = 'offline'
        loading = 11.22
        supervisor_url = 'http://offline.com'
        self.now_func.now = datetime.datetime.utcnow()
        with transaction.manager:
            model.update_host(host_ip, 'test', state, loading, supervisor_url)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, False)
        self.assertEqual(host.loading, loading)
        self.assertEqual(host.supervisor_url, supervisor_url)
        self.assertEqual(host.online_time, old_online_time)

    def test_update_broadcast(self):
        import transaction
        model = self.make_one()

        with transaction.manager:
            host = self.make_host(model)
            kwargs = dict(
                server_name='b1',
                host=host,
                type='broadcast',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10
            )
            model.update_server(**kwargs)

        server = model.get_server_by_name('b1')
        self.assertEqual(server.type, kwargs['type'])
        self.assertEqual(server.pid, kwargs['pid'])
        self.assertEqual(server.revision, kwargs['revision'])
        self.assertEqual(server.user_count, kwargs['user_count'])
        self.assertEqual(server.user_limit, kwargs['user_limit'])
        self.assertEqual(server.resource_count, kwargs['resource_count'])
        self.assertEqual(server.resource_limit, kwargs['resource_limit'])
        self.assertEqual(server.inbound_rate, kwargs['inbound_rate'])
        self.assertEqual(server.outbound_rate, kwargs['outbound_rate'])
        self.assertEqual(server.loading, kwargs['loading'])
        ports = {}
        for port in server.ports:
            ports[port.name] = port.address
        self.assertEqual(ports, kwargs['ports'])

        # update ports
        kwargs['ports'] = dict(web2='5.5.6.6')
        kwargs['user_count'] = 9999
        kwargs['state'] = 'normal'
        with transaction.manager:
            model.update_server(**kwargs)

        server = model.get_server_by_name('b1')
        self.assertEqual(server.user_count, 9999)
        ports = {}
        for port in server.ports:
            ports[port.name] = port.address
        self.assertEqual(ports, kwargs['ports'])

        # update ports
        def update_ports(ports):
            kwargs['ports'] = ports
            kwargs['state'] = 'normal'
            with transaction.manager:
                model.update_server(**kwargs)
            server = model.get_server_by_name(kwargs['server_name'])
            ports = {}
            for port in server.ports:
                ports[port.name] = port.address
            self.assertEqual(ports, kwargs['ports'])

        update_ports(dict(web2='7.7.8.8', web3='1.2.3.4'))
        update_ports(dict(web='7.7.7.7'))
        update_ports(dict())

    def test_update_proxy(self):
        import transaction
        model = self.make_one()

        with transaction.manager:
            host = self.make_host(model)
            kwargs = dict(
                server_name='p1',
                host=host,
                type='proxy',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10,
            )
            model.update_server(**kwargs)

        server = model.get_server_by_name('p1')
        self.assertEqual(server.type, kwargs['type'])
        self.assertEqual(server.pid, kwargs['pid'])
        self.assertEqual(server.revision, kwargs['revision'])
        self.assertEqual(server.user_count, kwargs['user_count'])
        self.assertEqual(server.user_limit, kwargs['user_limit'])
        self.assertEqual(server.resource_count, kwargs['resource_count'])
        self.assertEqual(server.resource_limit, kwargs['resource_limit'])
        self.assertEqual(server.inbound_rate, kwargs['inbound_rate'])
        self.assertEqual(server.outbound_rate, kwargs['outbound_rate'])
        self.assertEqual(server.loading, kwargs['loading'])
        ports = {}
        for port in server.ports:
            ports[port.name] = port.address
        self.assertEqual(ports, kwargs['ports'])

        # test radios for proxy and broadcast
        user_model = self.make_user_model()
        user_ids = []
        for i in range(4):
            name = 'user%s' % i
            user_id = user_model.create_user(name, name + '@now.in', '', '')
            user_model.activate_user(user_id, name, 'TW')
            user_ids.append(user_id)

        b_kwargs = dict(
            server_name='b1',
            host=host,
            type='broadcast',
            state='online',
            ports=dict(web='1.2.3.4'),
            pid=5566,
            revision='123',
            user_count=10,
            user_limit=20,
            resource_count=30,
            resource_limit=40,
            inbound_rate=55.66,
            outbound_rate=77.88,
            loading=10
        )
        with transaction.manager:
            model.update_server(**b_kwargs)
        broadcast = model.get_server_by_name('b1')
        with transaction.manager:
            model.add_on_airs(
                broadcast.name,
                [u'user0', u'user1', u'user2', u'user3']
            )

        return

    def test_update_on_airs(self):
        import transaction
        model = self.make_one()

        with transaction.manager:
            host = self.make_host(model)
            kwargs = dict(
                server_name='b1',
                host=host,
                type='broadcast',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10,
            )
            model.update_server(**kwargs)

        def update_radios(radios):
            with transaction.manager:
                model.update_on_airs('b1', radios)
            server = model.get_server_by_name('b1')
            radio_set = set(radios)
            result = set()
            for on_air in server.on_airs:
                result.add(on_air.user.user_name)
                self.assertEqual(on_air.server_id, server.id)
            self.assertEqual(result, radio_set)

        with transaction.manager:
            self.create_users(4)
        update_radios([u'user0', u'user1'])
        update_radios([u'user1', u'user2'])
        update_radios([])
        update_radios([u'user0', u'user1', u'user2', u'user3'])

    def test_update_proxy_connections(self):
        import transaction
        model = self.make_one()

        with transaction.manager:
            host = self.make_host(model)
            # create broadcast
            kwargs = dict(
                server_name='b1',
                host=host,
                type='broadcast',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10,
            )
            model.update_server(**kwargs)

        with transaction.manager:
            # create proxy
            kwargs = dict(
                server_name='p1',
                host=host,
                type='proxy',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10,
            )
            model.update_server(**kwargs)

        def update_radios(radios):
            with transaction.manager:
                model.update_proxy_connections('p1', radios)
            server = model.get_server_by_name('p1')
            result = {}
            for conn in server.connections:
                result[conn.on_air.user.user_name] = conn.listener
            self.assertEqual(result, radios)

        with transaction.manager:
            self.create_users(4)
            model.add_on_airs(
                'b1',
                [u'user0', u'user1', u'user2', u'user3']
            )
        update_radios({u'user0': 10, u'user1': 5, u'user2': 3})
        update_radios({u'user0': 5, u'user1': 10, u'user2': 20})
        update_radios({u'user0': 11, u'user1': 12})
        update_radios({u'user0': 13, u'user3': 14})
        update_radios({})

    def _create_server_for_on_air(self):
        model = self.make_one()

        host_ip = '127.0.0.1'
        name = 'test_host'
        alive = False
        loading = 55.66
        supervisor_url = 'http://now.in'

        host = model.add_host(
            host_ip=host_ip,
            name=name,
            alive=alive,
            loading=loading,
            supervisor_url=supervisor_url
        )

        def create_server(name):
            kwargs = dict(
                server_name=name,
                host=host,
                type='broadcast',
                state='online',
                ports=dict(web='1.2.3.4'),
                pid=5566,
                revision='123',
                user_count=10,
                user_limit=20,
                resource_count=30,
                resource_limit=40,
                inbound_rate=55.66,
                outbound_rate=77.88,
                loading=10
            )
            server = model.update_server(**kwargs)
            return server

        create_server('b1')
        create_server('b2')

        user_model = self.make_user_model()
        user_ids = []
        for i in range(4):
            name = 'user%s' % i
            user_id = user_model.create_user(name, name + '@now.in', '', '')
            user_model.activate_user(user_id, name, 'TW')
            user_ids.append(user_id)

        return 'b1', 'b2', user_ids

    def test_add_on_airs(self):
        import transaction
        model = self.make_one()
        with transaction.manager:
            s1, s2, user_ids = self._create_server_for_on_air()
        user_model = self.make_user_model()

        with transaction.manager:
            model.add_on_airs(s1, [u'user0', u'user1'])
            model.add_on_airs(s2, [u'user2'])

        server1 = model.get_server_by_name(s1)
        server2 = model.get_server_by_name(s2)
        users = [user_model.get_user_by_id(id) for id in user_ids]

        self.assertEqual(users[0].on_air.server_id, server1.id)
        self.assertEqual(users[1].on_air.server_id, server1.id)
        self.assertEqual(users[2].on_air.server_id, server2.id)
        self.assertEqual(users[3].on_air, None)

    def test_remove_on_airs(self):
        import transaction
        model = self.make_one()
        user_model = self.make_user_model()

        with transaction.manager:
            s1, s2, user_ids = self._create_server_for_on_air()

        with transaction.manager:
            model.add_on_airs(s1, [u'user0', u'user1'])
            model.add_on_airs(s2, [u'user2'])

        server1 = model.get_server_by_name(s1)
        server2 = model.get_server_by_name(s2)
        users = [user_model.get_user_by_id(id) for id in user_ids]

        self.assertEqual(users[0].on_air.server_id, server1.id)
        self.assertEqual(users[1].on_air.server_id, server1.id)
        self.assertEqual(users[2].on_air.server_id, server2.id)
        self.assertEqual(users[3].on_air, None)

        with transaction.manager:
            model.remove_on_airs(s1, [u'user0'])
            model.remove_on_airs(s2, [u'user2'])
            model.add_on_airs(s2, [u'user3'])

        server1 = model.get_server_by_name(s1)
        server2 = model.get_server_by_name(s2)
        users = [user_model.get_user_by_id(id) for id in user_ids]

        self.assertEqual(users[0].on_air, None)
        self.assertEqual(users[1].on_air.server_id, server1.id)
        self.assertEqual(users[2].on_air, None)
        self.assertEqual(users[3].on_air.server_id, server2.id)

    def test_expire_hosts(self):
        import transaction
        model = self.make_one()

        host_ip = '127.0.0.1'
        name = 'test_host'
        alive = True
        loading = 55.66
        supervisor_url = 'http://now.in'

        timeout = 5.5

        with transaction.manager:
            model.add_host(
                host_ip=host_ip,
                name=name,
                alive=alive,
                loading=loading,
                supervisor_url=supervisor_url
            )
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, True)
        self.assertEqual(host.last_updated, self.now_func.now)

        self.now_func.now += datetime.timedelta(seconds=4)
        with transaction.manager:
            model.expire_hosts(timeout)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, True)

        self.now_func.now += datetime.timedelta(seconds=10)
        with transaction.manager:
            model.expire_hosts(timeout)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, False)

        self.now_func.now += datetime.timedelta(seconds=10)
        with transaction.manager:
            model.update_host(
                host_ip=host_ip,
                name='test',
                state='online',
                loading=10,
                supervisor_url='http://now.in'
            )
            model.expire_hosts(timeout)
        host = model.get_host_by_ip(host_ip)
        self.assertEqual(host.alive, True)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingModel))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
