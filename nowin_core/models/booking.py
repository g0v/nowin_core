import datetime
import logging

from nowin_core.database import tables


class BookingModel(object):

    """Model for managing server status

    """

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_host_by_ip(self, host_ip):
        """Get host by IP

        """
        host = self.session.query(tables.Host).filter_by(ip=host_ip).first()
        return host

    def get_server_table(self, type):
        """Get server table by type

        """
        table_type = None
        if type == 'proxy':
            table_type = tables.Proxy
        elif type == 'broadcast':
            table_type = tables.Broadcast
        return table_type

    def get_server_by_name(self, server_name):
        """Get a server by name

        """
        server = self.session \
            .query(tables.Server) \
            .filter_by(name=server_name) \
            .first()
        return server

    def get_listener_count(self):
        """Get listener count for all radios

        """
        from sqlalchemy.sql.expression import func
        from sqlalchemy.sql.functions import sum
        OnAir = tables.OnAir
        User = tables.User
        Conn = tables.ProxyConnection

        query = self.session \
            .query(User.user_name, func.ifnull(sum(Conn.listener), 0)) \
            .join((OnAir, OnAir.user_id == User.user_id)) \
            .outerjoin((Conn, Conn.user_id == User.user_id)) \
            .group_by(User.user_id)

        radios = {}
        for name, count in query:
            radios[str(name)] = int(count)
        return radios

    def add_host(self, host_ip, name, alive, loading, supervisor_url=None):
        """Add a host and return

        """
        host = tables.Host(
            ip=host_ip,
            name=name,
            alive=alive,
            loading=loading,
            supervisor_url=supervisor_url,
            online_time=tables.now_func(),
            last_updated=tables.now_func(),
            created=tables.now_func()
        )
        self.session.add(host)
        self.session.flush()
        host = self.get_host_by_ip(host_ip)
        self.logger.info('Add host %s', host)

    def update_host(self, host_ip, name, state, loading, supervisor_url):
        """Update state of host

        """
        host = self.get_host_by_ip(host_ip)
        if state == 'online':
            host.online_time = tables.now_func()
            host.alive = True
            self.logger.info('Host %s goes online', host)
        elif state == 'offline':
            host.alive = False
            self.logger.info('Host %s goes offline', host)
        elif state == 'normal':
            # Listen to Still alive: http://www.youtube.com/watch?v=Y6ljFaKRTrI
            # :)
            # the server back online
            if not host.alive:
                self.logger.info('Host %s is back online', host)
            else:
                self.logger.info('Host %s is still alive', host)
            host.alive = True

        host.name = name
        host.loading = loading
        host.supervisor_url = supervisor_url
        host.last_updated = tables.now_func()
        self.session.add(host)
        self.session.flush()

    def update_server(
        self,
        server_name,
        type,
        host,
        state,
        ports,
        pid,
        revision,
        user_count,
        user_limit,
        resource_count,
        resource_limit,
        inbound_rate,
        outbound_rate,
        loading,
    ):
        """Update state of server

        server_name
            name of serverto update
        type
            type of server
        state
            current state of server heart beat
        ports
            ports of server, format should be
                dict(port_name=port_address, ...)
        pid
            pid of process
        revision
            revision of server
        user_count
            count of user
        user_limit
            limit of user
        resource_count
            count of resource
        resource_limit
            limit of resource
        inbound_rate
            inbound bandwidth
        outbound_rate
            outbound bandwidth
        loading
            loading of server

        radios
            map of listener count on proxy server or
            name of alive radios on braodcast server

        """
        now = tables.now_func()
        table_type = self.get_server_table(type)
        server = self.session \
            .query(table_type) \
            .filter_by(name=server_name) \
            .first()
        if server is None:
            server = table_type(name=server_name)
            server.created = now
            server.online_time = now
            self.logger.info('Add server %r', server_name)

        if state == 'online':
            server.online_time = now
            server.alive = True
            self.logger.info('Server %r goes online',
                             server.name)
        elif state == 'offline':
            server.alive = False
            self.logger.info('Server %r goes offline',
                             server.name)
        elif state == 'normal':
            # Listen to Still alive: http://www.youtube.com/watch?v=Y6ljFaKRTrI
            # :)
            if not server.alive:
                self.logger.info('Server %r is back online',
                                 server.name)
            else:
                self.logger.info('Server %r is still alive',
                                 server.name)
            server.alive = True

        # get all old ports
        old_ports = {}
        for port in server.ports:
            old_ports[port.name] = port
        old_set = set(old_ports)

        # get all new ports
        new_ports = ports
        new_set = set(new_ports)
        # set of port to update
        to_update = old_set & new_set
        # set of port to delete
        to_delete = old_set - to_update
        # set of port to add
        to_add = new_set - to_update

        self.logger.debug('old: %s, new: %s', old_set, new_set)
        self.logger.debug(
            'to_update: %s, to_delete: %s, to_add: %s',
            to_update, to_delete, to_add
        )

        # update old ports
        for name in to_update:
            port = old_ports[name]
            port.address = new_ports[name]
            self.session.add(port)
        # delete outdate ports
        for name in to_delete:
            port = old_ports[name]
            self.session.delete(port)
        # add new ports
        for name in to_add:
            address = new_ports[name]
            port = tables.Port(name=name, address=address)
            server.ports.append(port)
            self.session.add(port)

        server.host = host
        server.pid = pid
        server.revision = revision
        server.user_limit = user_limit
        server.user_count = user_count
        server.resource_limit = resource_limit
        server.resource_count = resource_count
        server.inbound_rate = inbound_rate
        server.outbound_rate = outbound_rate
        server.loading = loading
        server.last_updated = now

        self.session.add(server)
        self.session.flush()

    def update_proxy_connections(self, server_name, radios):
        """Update listener count of proxy connections

        radios is a dict mapping radio user_name to listener count
        """
        User = tables.User
        ProxyConnection = tables.ProxyConnection

        proxy = self.get_server_by_name(server_name)
        if proxy is None:
            msg = 'Update connection to non-exist server %s' % server_name
            self.logger.error(msg)
            raise Exception(msg)

        # old proxy connections
        old_conns = {}
        for conn in proxy.connections:
            old_conns[conn.user_id] = conn
        old_set = set(old_conns)

        # new proxy connections
        new_conns = {}
        for name, listener in radios.iteritems():
            new_conns[name] = listener
        new_set = set(new_conns)

        # set of port to update
        to_update = old_set & new_set
        # set of port to delete
        to_delete = old_set - to_update
        # set of port to add
        to_add = new_set - to_update

        # update old connection
        for name in to_update:
            conn = old_conns[name]
            conn.listener = new_conns[name]
            self.session.add(conn)

        # delete old connections
        for name in to_delete:
            conn = old_conns[name]
            self.session.delete(conn)

        # add new connections
        if to_add:
            users = self.session \
                .query(User) \
                .filter(User.user_name.in_(to_add))
            user_map = {}
            for user in users:
                user_map[user.user_name] = user.user_id
            for name in to_add:
                conn = ProxyConnection()
                conn.listener = new_conns[name]
                conn.user_id = user_map[name]
                proxy.connections.append(conn)
                self.session.add(conn)

        self.session.flush()
        self.logger.info('Update %s connections on proxy %r',
                         len(radios), proxy)

    def add_on_airs(self, server_name, radios):
        """Add on-air radios

        """
        from sqlalchemy.orm import joinedload
        if not radios:
            self.logger.info('No radio gets offline')
            return

        server = self.session \
            .query(tables.Broadcast) \
            .filter_by(name=server_name) \
            .first()
        if not server:
            self.logger.error('Radio gets online from a non-exist server %s',
                              server_name)
            return

        users = self.session \
            .query(tables.User) \
            .options(joinedload('on_air')) \
            .filter(tables.User.user_name.in_(radios)) \
            .all()
        for user in users:
            onair = user.on_air
            if not onair:
                onair = tables.OnAir()
            else:
                self.logger.warn('OnAir %s already exist', onair)
                continue
            onair.online_time = tables.now_func()
            onair.server_id = server.id
            user.on_air = onair
            self.session.add(server)
        self.session.flush()
        self.logger.info('Add on-air %s of broadcast %s',
                         len(radios), server_name)

    def update_on_airs(self, server_name, radios):
        """Update on-airs of a broadcast server

        radios is a list of current online radio user name
        """
        User = tables.User
        OnAir = tables.OnAir

        broadcast = self.get_server_by_name(server_name)
        if broadcast is None:
            msg = 'Update on-air to non-exist server %s' % server_name
            self.logger.error(msg)
            raise Exception(msg)

        radios = map(unicode, radios)

        # get old on-airs
        old_on_airs = set([on_air.user_id for on_air in broadcast.on_airs])
        # get new current on-airs
        if radios:
            users = self.session \
                .query(User) \
                .filter(User.user_name.in_(radios)) \
                .all()
            new_on_airs = set([user.user_id for user in users])
        else:
            new_on_airs = set()

        # the set of on-air that we don't have to do anything with them
        remain_on_airs = old_on_airs & new_on_airs
        # to delete on-airs
        to_delete = old_on_airs - remain_on_airs
        # to add on_airs
        to_add = new_on_airs - remain_on_airs

        # delete off-line radios
        if to_delete:
            self.session \
                .query(OnAir) \
                .filter(OnAir.user_id.in_(to_delete)) \
                .delete('fetch')
        # add online radios
        for user_id in to_add:
            on_air = OnAir(
                server_id=broadcast.id,
                user_id=user_id,
                online_time=tables.now_func()
            )

            self.session.add(on_air)
        self.session.flush()
        self.logger.info('Update on-air %s of broadcast %s',
                         len(radios), server_name)

    def remove_on_airs(self, server_name, radios):
        """Remove on-air radios

        """
        from sqlalchemy.orm import joinedload

        if not radios:
            self.logger.info('No radio gets offline')
            return

        server = self.session \
            .query(tables.Broadcast) \
            .filter_by(name=server_name) \
            .first()
        if not server:
            self.logger.error('Radio gets offline with non-exist server %s ',
                              server_name)
            return

        users = self.session \
            .query(tables.User) \
            .options(joinedload('on_air')) \
            .filter(tables.User.user_name.in_(radios)) \
            .all()
        for user in users:
            onair = user.on_air
            if not onair:
                self.logger.error('OnAir broadcast=%s, user=%s does not exist',
                                  server, user)
                continue
            self.session.delete(onair)
            self.logger.info('Remove on-air %s', onair)
        self.session.flush()
        self.logger.info('Remove on-air %s of broadcast %s',
                         len(radios), server_name)

    def get_source_address(self, user_name):
        """Get address of audio source of broadcast server

        """
        from sqlalchemy.orm import joinedload

        # make sure the user is online
        user = self.session.query(tables.User). \
            options(joinedload('on_air.broadcast')). \
            filter_by(user_name=user_name).first()
        if user is None or user.on_air is None:
            self.logger.info('Radio %r is not on-air', user_name)
            return

        # get address of
        port = self.session.query(tables.Port) \
            .filter_by(server_id=user.on_air.broadcast.id, name='stream') \
            .first()
        if port is None:
            self.logger.info('Cannot find source address for %s', user_name)
            return
        address = port.address
        self.logger.info(
            'Radio %r audio resource is on %r', user_name, address)
        return address

    def expire_hosts(self, timeout):
        """set hosts whose last_updated is before current - timeout as dead

        """
        from sqlalchemy.sql.expression import func, text
        Host = tables.Host
        # delete out-dated hosts
        # func.timestampadd()
        now = tables.now_func()
        if isinstance(now, datetime.datetime):
            deadline = now - datetime.timedelta(seconds=timeout)
        else:
            deadline = func.timestampadd(text('second'), -timeout, now)
        query = self.session \
            .query(Host) \
            .filter(Host.alive) \
            .filter(Host.last_updated < deadline)
        count = query.count()
        query.update(dict(alive=False), False)
        self.session.flush()
        self.logger.info('Expire %s hosts', count)

    def expire_servers(self, timeout):
        """set servers whose last_updated is before current - timeout as dead

        """
        from sqlalchemy.sql.expression import func, text
        Server = tables.Server
        OnAir = tables.OnAir
        now = tables.now_func()
        if isinstance(now, datetime.datetime):
            deadline = now - datetime.timedelta(seconds=timeout)
        else:
            deadline = func.timestampadd(text('second'), -timeout, now)
        query = self.session \
            .query(Server.id) \
            .filter(Server.alive) \
            .filter(Server.last_updated < deadline)
        # delete on airs of broadcast server
        broadcasts = query \
            .filter_by(type='broadcast') \
            .subquery()
        self.session \
            .query(OnAir) \
            .filter(OnAir.server_id.in_(broadcasts)) \
            .delete('fetch')
        # update server state to dead
        count = query.count()
        query.update(dict(alive=False), False)
        self.session.flush()
        self.logger.info('Expire %s servers', count)
