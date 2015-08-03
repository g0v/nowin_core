import logging

from nowin_core.database import tables


class CustomModel(object):

    """Model for custom radio pages

    """

    def __init__(self, session, commit_func=None, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session
        self.commit_func = commit_func

    def _commit(self):
        if self.commit_func is None:
            import transaction
            transaction.commit()
        else:
            self.commit_func()

    def getNewsByUserID(self, user_id):
        """Get news by user id

        """
        news = self.session \
            .query(tables.CustomNews) \
            .filter_by(user_id=user_id) \
            .order_by(tables.CustomNews.order)
        return news

    def getNewsByID(self, news_id):
        """Get news by news id

        """
        news = self.session.query(tables.CustomNews).get(news_id)
        return news

    def addNews(
        self,
        user_id,
        order,
        title,
        url,
        source
    ):
        """Add a custom radio page news

        """
        news = tables.CustomNews(
            user_id=user_id,
            order=order,
            title=title,
            url=url,
            source=source
        )
        self.session.add(news)
        self.session.flush()
        news_id = news.id
        self._commit()
        return news_id

    def removeNews(self, news_id):
        """Remove a custom radio page news

        """
        news = self.session.query(tables.CustomNews).get(news_id)
        self.session.delete(news)
        self._commit()

    def updateNews(self, news_id, order, title, url, source):
        """Update a custom radio page news

        """
        news = self.session.query(tables.CustomNews).get(news_id)
        news.order = order
        news.title = title
        news.url = url
        news.source = source
        self.session.add(news)
        self._commit()
