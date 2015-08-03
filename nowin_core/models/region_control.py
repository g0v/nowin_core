import logging

from nowin_core.database import tables


class RegionControlModel(object):

    """This model provides region controlling information

    """

    COUNTRY_INCLUDE = 0
    COUNTRY_EXCLUDE = 1

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_country_limit(self, user_id):
        """Get country limitation information

        given an user_id, return  (include_or_exclude, codes)

        """
        site = self.session.query(tables.Site).get(user_id)
        if site is None:
            raise KeyError('Site of %s does not existe' % user_id)
        query = self.session \
            .query(tables.CountryLimit) \
            .filter_by(user_id=user_id)
        codes = []
        for limit in query:
            codes.append(limit.code)
        return site.country_limit, codes

    def update_country_limit(self, user_id, include_or_exclude, codes):
        """Update country limitation for audiences of a radio

        For example, to allow only two countries TW and JP, here you call

            update_country_limit(
                user_id,
                AudienceLimitModel.COUNTRY_INCLUDE,
                ['TW', 'JP']
            )

        Allow global audiences, but exclude some countries, here you call

            update_country_limit(
                user_id,
                AudienceLimitModel.COUNTRY_EXCLUDE,
                ['TW', 'JP']
            )

        """
        l = [self.COUNTRY_INCLUDE, self.COUNTRY_EXCLUDE]
        if (include_or_exclude not in l):
            raise ValueError('Unknown')
        site = self.session.query(tables.Site).get(user_id)
        if site is None:
            raise KeyError('Site of %s does not exist' % user_id)
        site.country_limit = include_or_exclude
        self.session.add(site)

        # delete old country limits
        self.session \
            .query(tables.CountryLimit) \
            .filter_by(user_id=user_id) \
            .delete()

        for code in codes:
            limit = tables.CountryLimit(user_id=user_id, code=code)
            self.session.add(limit)

    def is_country_allowed(self, user_id, code):
        """Determine are users from a country allowed to access a radio

        """
        include_or_exclude, codes = self.get_country_limit(user_id)
        code = code.lower()
        codes = map(lambda c: c.lower(), codes)
        if include_or_exclude == self.COUNTRY_INCLUDE:
            if code in codes:
                return True
        else:
            if code not in codes:
                return True
        return False
