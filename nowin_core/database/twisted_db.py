import logging
import threading

import sqlalchemy
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from twisted.internet import threads


class Database(object):

    def __init__(self, use_transaction=False, logger=None):
        self.logger = logger
        self._local = threading.local()
        self.use_transaction = use_transaction

    def bind(self, url=None, init_tables=True, *args, **kwargs):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        self.engine = sqlalchemy.create_engine(url, *args, **kwargs)
        if init_tables:
            self.initTables()
        self.logger.info('Bound database')

    def initTables(self):
        from nowin_core.database import tables
        tables.initdb(self.engine)
        self.logger.info('Bound tables')

    def makeSession(self):
        # TODO: Maybe we can find a better way to determine MainThread
        assert threading.currentThread().name != 'MainThread', \
            "Sessions can not be made in the main thread, please use " \
            "decorator 'workWithDatabase' to decorate your function"
        assert hasattr(self._local, 'session_maker'), \
            "You have to run your function with workWithDatabase(func) "
        return self._local.session_maker()

    def workWithDatabase(self, func):
        from functools import wraps

        @wraps(func)
        def runInThread(*args, **kwargs):
            extra_args = {}
            if self.use_transaction:
                from zope.sqlalchemy import ZopeTransactionExtension
                extra_args['extension'] = ZopeTransactionExtension()
            self._local.session_maker = scoped_session(
                sessionmaker(
                    bind=self.engine,
                    autocommit=False,
                    autoflush=False,
                    **extra_args
                )
            )
            self.logger.debug(
                'Make thread-local session maker %s in thread %s',
                self._local.session_maker,
                threading.currentThread()
            )
            try:
                return func(*args, **kwargs)
            except:
                self.logger.error('Error when work with database in func %r',
                                  func.__name__, exc_info=True)
            finally:
                self._local.session_maker.remove()
                del self._local.session_maker
                self.logger.debug('Remove thread-local session maker in '
                                  'thread %s', threading.currentThread())

        @wraps(func)
        def decorated(*args, **kwargs):
            return threads.deferToThread(runInThread, *args, **kwargs)
        return decorated

db = Database()
