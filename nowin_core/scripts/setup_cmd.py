from distutils.core import Command


def get_config():
    """Read configuration file and return

    """
    import os
    import yaml
    import nowin_core

    dir_name, _ = os.path.split(os.path.dirname(nowin_core.__file__))
    path = os.path.join(dir_name, 'config.yaml')
    key = 'NOWIN_CORE_CONFIG'
    if key in os.environ:
        path = os.environ[key]
    config = yaml.load(open(path, 'rt'))
    return config


def setup_db(config=None, uri=None, echo=False):
    """Setup database

    """
    from sqlalchemy import create_engine
    from nowin_core.database.tables import initdb
    if config is None:
        config = get_config()
    if uri is None:
        uri = config['database']['uri']
    engine = create_engine(uri, convert_unicode=True, echo=echo)
    initdb(engine)
    return engine


class InitdbCommand(Command):
    description = "initialize database"
    user_options = [
        ('uri=', 'u', 'URI of SQLAlchemy database engine to initialize')
    ]

    def initialize_options(self):
        self.uri = None

    def finalize_options(self):
        if self.uri is None:
            config = get_config()
            self.uri = config['database']['uri']

    def run(self):
        engine = setup_db(uri=self.uri, echo=True)

        from nowin_core.database.tables import DeclarativeBase
        DeclarativeBase.metadata.create_all(bind=engine)

        import getpass
        import transaction
        from ..database import tables
        from ..models.user import UserModel
        from ..models.group import GroupModel
        from ..models.permission import PermissionModel

        session = tables.DBSession

        from zope.sqlalchemy import ZopeTransactionExtension
        session.configure(extension=ZopeTransactionExtension())

        user_model = UserModel(session)
        group_model = GroupModel(session)
        permission_model = PermissionModel(session)

        with transaction.manager:
            admin = user_model.get_user_by_name('admin')
            if admin is None:
                print 'Create admin account'

                email = raw_input('Email:')

                password = getpass.getpass('Password:')
                confirm = getpass.getpass('Confirm:')
                if password != confirm:
                    print 'Password not match'
                    return

                user_id = user_model.create_user(
                    user_name='admin',
                    display_name='Administrator',
                    email=email,
                    password=password
                )
                user_model.activate_user(user_id, '', 'TW')
                admin = user_model.get_user_by_id(user_id)
                session.flush()
                print 'Created admin, user_id=%s' % admin.user_id

            permission = permission_model.get_permission_by_name('admin')
            if permission is None:
                print 'Create admin permission ...'
                permission_model.create_permission(
                    permission_name='admin',
                    description='Administrate',
                )
                permission = permission_model.get_permission_by_name('admin')

            group = group_model.get_group_by_name('admin')
            if group is None:
                print 'Create admin group ...'
                group_model.create_group(
                    group_name='admin',
                    display_name='Administrators',
                )
                group = group_model.get_group_by_name('admin')

            print 'Add admin permission to admin group'
            group_model.update_permissions(
                group.group_id, [permission.permission_id])
            session.flush()

            print 'Add admin to admin group'
            user_model.update_groups(admin.user_id, [group.group_id])
            session.flush()

        print 'Done.'


class ShellCommand(Command):
    description = "open a shell"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import code
        from nowin_core.database import tables
        from nowin_core.models.user import UserModel
        from nowin_core.models.booking import BookingModel
        from nowin_core.models.radio import RadioModel
        from nowin_core.utils import createTestingAccounts

        setup_db(echo=False)
        user_model = UserModel(tables.DBSession)
        booking_model = BookingModel(tables.DBSession)
        radio_model = RadioModel(tables.DBSession)
        local = dict(
            session=tables.DBSession,
            tables=tables,
            user_model=user_model,
            booking_model=booking_model,
            radio_model=radio_model,
            createTestingAccounts=createTestingAccounts
        )
        code.interact(
            banner="""# nowin_core console

variables:
    session - session for database
    tables - nowin_core.database.tables
    user_model - UserModel
    booking_model - BookingModel
    radio_model - RadioModel

functions:
    createTestingAccounts - Create many testing accounts

""",
            local=local
        )
