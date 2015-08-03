import logging

from nowin_core.database import tables


class StatsModel(object):

    """Stats model

    """

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_new_user_stats(self, begin, end):
        """Get statstic of new user

        """
        from sqlalchemy.sql.expression import func

        user_count = func.count(tables.User.user_id).label('user_count')
        date = func.date(tables.User.created).label('date')

        query = self.session.query(date, user_count) \
            .group_by(date) \
            .filter(func.date(tables.User.created) >= begin) \
            .filter(func.date(tables.User.created) <= end)
        return query.all()

    def get_user_stats(self):
        """Get statsics of user

        """
        import datetime
        from nowin_core.models.user import UserModel

        user_count = self.session.query(tables.User).count()
        activated_user_count = self.session.query(tables.Site).count()

        def filtered_user_count(**kwargs):
            return int(
                self.session.query(tables.User)
                    .filter_by(**kwargs).count()
            )
        gender = dict(
            male=filtered_user_count(gender=UserModel.GENDER_MALE),
            female=filtered_user_count(gender=UserModel.GENDER_FEMALE),
            other=filtered_user_count(gender=UserModel.GENDER_OTHER),
        )
        blood_type = dict(
            a=filtered_user_count(blood_type=UserModel.BLOOD_TYPE_A),
            b=filtered_user_count(blood_type=UserModel.BLOOD_TYPE_B),
            ab=filtered_user_count(blood_type=UserModel.BLOOD_TYPE_AB),
            o=filtered_user_count(blood_type=UserModel.BLOOD_TYPE_O),
        )
        age = {}
        today = datetime.date.today()
        year5 = datetime.timedelta(days=365 * 5)

        begin = today - year5
        end = today
        for current_age in xrange(0, 100, 5):
            count = self.session.query(tables.User) \
                .filter(tables.User.birthday > begin) \
                .filter(tables.User.birthday <= end) \
                .count()
            age['%s_%s' % (current_age, current_age + 4)] = count
            begin -= year5
            end -= year5

        return dict(
            user_count=user_count,
            activated_user_count=activated_user_count,
            gender=gender,
            blood_type=blood_type,
            age=age
        )

    def get_country_stats(self):
        """Get country list order by online listener count

        """
        from sqlalchemy import distinct
        from sqlalchemy.sql.expression import func, desc
        from sqlalchemy.sql.functions import sum

        # table short cut
        Site = tables.Site
        OnAir = tables.OnAir
        ProxyConnection = tables.ProxyConnection
        listener_count = func.ifnull(sum(ProxyConnection.listener), 0) \
            .label('listener_count')
        radio_count = func.ifnull(func.count(distinct(Site.user_id)), 0) \
            .label('radio_count')
        locations = self.session \
            .query(Site.location, listener_count, radio_count) \
            .join((OnAir, OnAir.user_id == Site.user_id)) \
            .outerjoin((ProxyConnection, ProxyConnection.user_id == Site.user_id)) \
            .group_by(Site.location) \
            .order_by(desc('listener_count'))
        return locations.all()

    def get_on_air_stats(self):
        """Get stats of on-air radios

        """
        from sqlalchemy.sql.expression import func
        from sqlalchemy.sql.functions import sum

        def sum_or_0(column):
            return func.ifnull(sum(column), 0)

        # total on air radios
        radio_count = self.session.query(tables.OnAir).count()
        # total listener count
        listener_count = self.session.query(
            sum_or_0(tables.Server.user_count)
        ).filter_by(type='proxy').filter_by(alive=True).one()[0]
        return dict(
            radio_count=radio_count,
            listener_count=listener_count
        )
