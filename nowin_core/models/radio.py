import logging
import random

from nowin_core.database import tables


class RadioModel(object):

    """Radio data model

    """

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_host_by_ip(self, ip):
        """Get host by ip

        """
        return self.session.query(tables.Host).filter_by(ip=ip).first()

    def get_host_by_name(self, name):
        """Get host by name

        """
        return self.session.query(tables.Host).filter_by(name=name).first()

    def get_on_air(self, user_id):
        """Get on-air by user_id

        """
        OnAir = tables.OnAir
        on_air = self.session \
            .query(OnAir) \
            .filter_by(user_id=user_id) \
            .first()
        return on_air

    def get_broadcast_address(self, ip_address=None, best=2):
        """Get a usable broadcast address and return, if there is no available
        server, return None instead

        ip_address is an optional argument, we might use it to get the near
        server by geo-location

        """
        from sqlalchemy.sql.expression import or_, cast
        from sqlalchemy.types import Float

        Broadcast = tables.Broadcast
        Port = tables.Port
        # TODO:
        # route by GEO ip?

        # Cast the type to make sure the result will be float
        res_rate = (Broadcast.resource_count /
                    cast(Broadcast.resource_limit, Float))

        user_rate = (Broadcast.user_count /
                     cast(Broadcast.user_limit, Float))

        # order by loading, get best of them
        ports = self.session \
            .query(Port) \
            .join((Broadcast, Broadcast.id == Port.server_id)) \
            .order_by(res_rate) \
            .order_by(user_rate) \
            .filter(or_(Broadcast.user_count < Broadcast.user_limit,
                        Broadcast.user_limit == 0)) \
            .filter(or_(Broadcast.resource_count < Broadcast.resource_limit,
                        Broadcast.resource_limit == 0)) \
            .filter(Broadcast.alive) \
            .filter(Broadcast.active) \
            .filter(Port.name == 'source') \
            .limit(best) \
            .all()

        if not ports:
            return
        # randomly select from best server
        port = random.choice(ports)
        return port.address

    def get_proxy_address(
        self,
        user_id,
        ip_address=None,
        best=4,
        conn_factor=0.2
    ):
        """Get a usable proxy address for audio resource of user by user_id.
        If there is no available server, None will be returned

        We sort the connection by

            user_rate - (have_conn*conn_factor) then
            res_rate - (have_conn*conn_factor)

        Which means, less user proxy will be selected first, also, if there
        is already a proxy connection there, they will have higher priority
        (introduced by the conn_factor).

        """
        from sqlalchemy.sql.expression import or_, and_, cast, case
        from sqlalchemy.types import Float

        Port = tables.Port
        Proxy = tables.Proxy
        ProxyConnection = tables.ProxyConnection

        # calculate the connection factor
        factor_case = case([
            (ProxyConnection.server_id, conn_factor)
        ], else_=0)

        # Cast the type to make sure the result will be float
        res_rate = (Proxy.resource_count / cast(Proxy.resource_limit, Float))
        res_rate -= factor_case

        user_rate = (Proxy.user_count / cast(Proxy.user_limit, Float))
        user_rate -= factor_case

        query = self.session \
            .query(Port) \
            .join((Proxy, Proxy.id == Port.server_id)) \
            .outerjoin((ProxyConnection,
                        and_(ProxyConnection.server_id == Proxy.id,
                             ProxyConnection.user_id == user_id))) \
            .order_by(user_rate) \
            .order_by(res_rate) \
            .filter(or_(Proxy.user_count < Proxy.user_limit,
                        Proxy.user_limit == 0)) \
            .filter(Proxy.alive) \
            .filter(Proxy.active) \
            .filter(Port.name == 'web')

        # find a random proxy
        ports = query.limit(best).all()
        if not ports:
            return None
        port = random.choice(ports)
        return port.address

    def get_sites(
        self,
        offset=None,
        limit=None,
        on_air=True,
        keywords=None,
        radio_names=None,
        public=True,
        locations=None,
        exclude_locations=None,
        tags=None,
        ids=None,
        order_by=None,
        return_count=False,
        load_user=True,
        load_tags=True,
    ):
        """Get query of on air sites

        if on_air is true, only on air radio sites will be returned, if
        it's false, only offline radio sites will be return, otherwise,
        all sites will be returned

        order_by can be 'listener_count', 'online_time' or None

        radio_names is list of user name of radio to filter

        public is same as on_air but for filtering public and private sites

        location is the location of site to filter

        ids is a list of user_id

        if return_count is Ture, the result will be count of data only

        load_user indicate whether to load user eagerly
        load_tags indicate whether to load tags eagerly

        """
        from sqlalchemy.sql.expression import func, not_, desc, or_
        from sqlalchemy.orm import joinedload
        from sqlalchemy.sql.functions import sum

        assert order_by in [None, 'listener_count', 'online_time']

        # table short cut
        User = tables.User
        Site = tables.Site
        OnAir = tables.OnAir
        ProxyConnection = tables.ProxyConnection
        Tag = tables.Tag
        SiteTag = tables.SiteTag

        listener_count = func.ifnull(sum(ProxyConnection.listener), 0) \
            .label('listener_count')
        sites = self.session \
            .query(Site, listener_count) \
            .outerjoin((OnAir, OnAir.user_id == Site.user_id)) \
            .outerjoin((ProxyConnection, ProxyConnection.user_id == Site.user_id)) \
            .group_by(Site.user_id)

        # only on air sites
        if on_air is True:
            sites = sites.filter(OnAir.user_id is not None)
        elif on_air is False:
            sites = sites.filter(OnAir.user_id is None)

        # conditions
        if keywords is not None:
            ors = []
            for keyword in keywords:
                ors.append(Site.title.like('%%%s%%' % keyword))
                ors.append(Site.brief.like('%%%s%%' % keyword))
                ors.append(Site.description.like('%%%s%%' % keyword))
            user_ids = self.session.query(User.user_id) \
                .filter(User.user_name.in_(keywords)) \
                .subquery()
            user_ids_by_tag = self.session \
                .query(Site.user_id) \
                .join((SiteTag,
                       SiteTag.user_id == Site.user_id)) \
                .join((Tag, SiteTag.tag_id == Tag.id)) \
                .filter(Tag.name.in_(keywords)) \
                .subquery()
            ors.append(Site.user_id.in_(user_ids))
            ors.append(Site.user_id.in_(user_ids_by_tag))
            sites = sites.filter(or_(*ors))
        if ids is not None:
            sites = sites.filter(Site.user_id.in_(ids))
        if radio_names is not None:
            user_ids = self.session.query(User.user_id) \
                .filter(User.user_name.in_(radio_names)) \
                .subquery()
            sites = sites.filter(Site.user_id.in_(user_ids))
        if public is True:
            sites = sites.filter(Site.public is True)
        elif public is False:
            sites = sites.filter(Site.public is False)
        if locations is not None:
            locations = map(lambda x: x.upper(), locations)
            sites = sites.filter(Site.location.in_(locations))
        if exclude_locations is not None:
            sites = sites.filter(not_(Site.location.in_(exclude_locations)))
        if tags is not None:
            ids = self.session \
                .query(Site.user_id) \
                .join((SiteTag,
                       SiteTag.user_id == Site.user_id)) \
                .join((Tag, SiteTag.tag_id == Tag.id)) \
                .filter(Tag.name.in_(tags)) \
                .subquery()
            sites = sites.filter(Site.user_id.in_(ids))

        # all we need is count of data
        if return_count:
            return sites.count()

        # set the order
        if order_by is not None:
            if order_by == 'listener_count':
                sites = sites.order_by(desc('listener_count'))
            elif order_by == 'online_time':
                sites = sites.order_by(desc(OnAir.online_time))

        # offset and limit
        if offset is not None:
            sites = sites.offset(offset)
        if limit is not None:
            sites = sites.limit(limit)

        sites = sites.all()

        # eager load
        ids = [site.user_id for site, _ in sites]
        query = self.session.query(Site)
        if load_user:
            query = query.options(joinedload('user'))
        if load_tags:
            query = query.options(joinedload('tags'))
        query = query.filter(Site.user_id.in_(ids))

        query.all()

        return sites

    def get_country_list(self, limit=30):
        """Get country list order by online listener count

        """
        from sqlalchemy.sql.expression import func, desc
        from sqlalchemy.sql.functions import sum

        # table short cut
        Site = tables.Site
        OnAir = tables.OnAir
        ProxyConnection = tables.ProxyConnection
        listener_count = func.ifnull(sum(ProxyConnection.listener), 0) \
            .label('listener_count')
        locations = self.session \
            .query(Site.location, listener_count) \
            .join((OnAir, OnAir.user_id == Site.user_id)) \
            .filter((Site.public is True)) \
            .outerjoin((ProxyConnection, ProxyConnection.user_id == Site.user_id)) \
            .group_by(Site.location) \
            .order_by(desc('listener_count')) \
            .limit(limit)
        return locations.all()
