def create_session(echo=False, zope_transaction=True):
    """Create engine and session, return session then

    """
    from sqlalchemy import create_engine
    from nowin_core.database.tables import initdb
    from zope.sqlalchemy import ZopeTransactionExtension

    engine = create_engine('sqlite:///', convert_unicode=True, echo=echo)
    initdb(engine)
    from nowin_core.database.tables import DeclarativeBase, DBSession
    DeclarativeBase.metadata.create_all(bind=engine)
    DBSession.configure(bind=engine,
                        extension=ZopeTransactionExtension())
    if zope_transaction:
        DBSession.configure(extension=ZopeTransactionExtension())
    return DBSession
