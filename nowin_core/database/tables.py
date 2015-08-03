import os
import warnings
from hashlib import sha1

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import synonym
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import func

DeclarativeBase = declarative_base()

DBSession = scoped_session(sessionmaker(autocommit=False,
                                        autoflush=False))

_now_func = [func.utc_timestamp]


def set_now_func(func):
    """Replace now function and return the old function

    """
    old = _now_func[0]
    _now_func[0] = func
    return old


def get_now_func():
    """Return current now func

    """
    return _now_func[0]


def now_func():
    """Return current datetime

    """
    func = _now_func[0]
    return func()


def initdb(engine):
    DeclarativeBase.metadata.bind = engine

# { Association tables


# This is the association table for the many-to-many relationship between
# groups and permissions. This is required by repoze.what.
group_permission_table = Table(
    'group_permission',
    DeclarativeBase.metadata,
    Column(
        'group_id',
        Integer,
        ForeignKey('group.group_id', onupdate="CASCADE", ondelete="CASCADE")
    ),
    Column(
        'permission_id',
        Integer,
        ForeignKey(
            'permission.permission_id', onupdate="CASCADE", ondelete="CASCADE")
    )
)

# This is the association table for the many-to-many relationship between
# groups and members - this is, the memberships. It's required by repoze.what.
user_group_table = Table(
    'user_group',
    DeclarativeBase.metadata,
    Column(
        'user_id',
        Integer,
        ForeignKey('user.user_id', onupdate="CASCADE", ondelete="CASCADE")
    ),
    Column(
        'group_id',
        Integer,
        ForeignKey('group.group_id', onupdate="CASCADE", ondelete="CASCADE")
    )
)


# This is the association table for the many-to-many relationship between
# tags and sites
class SiteTag(DeclarativeBase):
    __tablename__ = 'site_tag'

    user_id = Column(Integer,
                     ForeignKey('user.user_id',
                                ondelete='CASCADE', onupdate='CASCADE'),
                     primary_key=True)

    tag_id = Column(Integer,
                    ForeignKey('tag.id',
                               ondelete='CASCADE', onupdate='CASCADE'),
                    primary_key=True)


class Blocking(DeclarativeBase):
    __tablename__ = 'blocking'

    owner_id = Column(
        Integer,
        ForeignKey(
            'user.user_id',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        primary_key=True
    )

    target_id = Column(
        Integer,
        ForeignKey(
            'user.user_id',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        primary_key=True
    )


class Following(DeclarativeBase):
    __tablename__ = 'following'

    owner_id = Column(
        Integer,
        ForeignKey(
            'user.user_id',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        primary_key=True
    )

    target_id = Column(
        Integer,
        ForeignKey(
            'user.user_id',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        primary_key=True
    )


class Group(DeclarativeBase):

    """
    Group definition for :mod:`repoze.what`.

    Only the ``group_name`` column is required by :mod:`repoze.what`.

    """

    __tablename__ = 'group'

    group_id = Column(Integer, autoincrement=True, primary_key=True)

    group_name = Column(Unicode(16), unique=True, nullable=False)

    display_name = Column(Unicode(255))

    created = Column(DateTime, default=now_func)

    users = relation('User', secondary=user_group_table, backref='groups')

    def __unicode__(self):
        return self.group_name


class PrivacyOption(DeclarativeBase):
    __tablename__ = 'privacy_option'

    user_id = Column(Integer,
                     ForeignKey('user.user_id',
                                ondelete='CASCADE', onupdate='CASCADE'),
                     primary_key=True)

    #: name of privacy option
    name = Column(Unicode(32), primary_key=True)

    #: value of privacy option
    value = Column(Integer)


class User(DeclarativeBase):

    """
    User definition.

    This is the user definition used by :mod:`repoze.who`, which requires at
    least the ``user_name`` column.

    """
    __tablename__ = 'user'

    user_id = Column(Integer, autoincrement=True, primary_key=True)

    user_name = Column(Unicode(16), unique=True, nullable=False)

    email = Column(Unicode(255), unique=True, nullable=False)

    display_name = Column(Unicode(255))

    _password = Column('password', Unicode(80))

    created = Column(DateTime, default=now_func)

    # is this account enable
    enable = Column(Boolean, default=True)
    # user profile
    profile = Column(UnicodeText(4096))

    # image name of this radio
    image_name = Column(Unicode(64))

    # gender of user, 0=female, 1=male, 2=other
    gender = Column(Integer)

    # birthday of user
    birthday = Column(Date)

    # blood type of user, 0=A, 1=B, 2=AB, 3=O
    blood_type = Column(Integer)

    # RelationShipExistp
    relationship = Column(Unicode(32))

    # link of website
    website_link = Column(Unicode(128))

    # site of this user
    site = relation("Site", uselist=False,
                    cascade="all, delete-orphan", backref="user")

    # on air radio of this user
    on_air = relation("OnAir", uselist=False,
                      cascade="all, delete-orphan", backref="user")

    # verifications of this user
    verifications = relation("Verification", cascade="all, delete-orphan",
                             backref="user")

    def __unicode__(self):
        return self.display_name or self.user_name

    @property
    def permissions(self):
        """Return a set of strings for the permissions granted."""
        perms = set()
        for g in self.groups:
            perms = perms | set(g.permissions)
        return perms

    @classmethod
    def by_email(cls, email):
        """Return the user object whose email address is ``email``."""
        warnings.warn("deprecated", DeprecationWarning)
        return DBSession.query(cls).filter(cls.email == email).first()

    @classmethod
    def by_user_name(cls, username):
        """Return the user object whose user name is ``username``."""
        warnings.warn("deprecated", DeprecationWarning)
        return DBSession.query(cls).filter(cls.user_name == username).first()

    def _set_password(self, password):
        """Hash ``password`` on the fly and store its hashed version."""
        # Workaround of the bug when debugging
        if isinstance(password, property):
            return

        if isinstance(password, unicode):
            password_8bit = password.encode('UTF-8')
        else:
            password_8bit = password

        salt = sha1()
        salt.update(os.urandom(60))
        hash = sha1()
        hash.update(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash.hexdigest()

        # Make sure the hashed password is an UTF-8 object at the end of the
        # process because SQLAlchemy _wants_ a unicode object for Unicode
        # columns
        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')

        self._password = hashed_password

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    password = synonym('_password', descriptor=property(_get_password,
                                                        _set_password))

    def validate_password(self, password):
        """
        Check the password against existing credentials.

        :param password: the password that was provided by the user to
            try and authenticate. This is the clear text version that we will
            need to match against the hashed one in the database.
        :type password: unicode object.
        :return: Whether the password is valid.
        :rtype: bool

        """
        hashed_pass = sha1()
        hashed_pass.update(password + self.password[:40])
        return self.password[40:] == hashed_pass.hexdigest()

    @property
    def active(self):
        """Return is this account active"""
        session = Session.object_session(self)
        verfication = session.query(Verification).\
            filter_by(user=self, passed=True).first()
        return verfication is not None and self.enable

    @property
    def follower_count(self):
        """Get count of follower

        """
        session = Session.object_session(self)
        return session.query(Following) \
            .filter_by(target_id=self.user_id) \
            .count()

    @property
    def listener_count(self):
        """Return listener count of radio

        """
        from sqlalchemy.sql.functions import sum
        from sqlalchemy.sql.expression import func
        session = Session.object_session(self)
        return session.query(func.ifnull(sum(ProxyConnection.listener), 0)) \
            .filter_by(user_id=self.user_id) \
            .one()


class Permission(DeclarativeBase):

    """
    Permission definition for :mod:`repoze.what`.

    Only the ``permission_name`` column is required by :mod:`repoze.what`.

    """

    __tablename__ = 'permission'

    permission_id = Column(Integer, autoincrement=True, primary_key=True)

    permission_name = Column(Unicode(16), unique=True, nullable=False)

    description = Column(Unicode(255))

    groups = relation(Group, secondary=group_permission_table,
                      backref='permissions')

    def __unicode__(self):
        return self.permission_name


class Site(DeclarativeBase):
    __tablename__ = 'site'

    # the owner user's id
    user_id = Column(Integer,
                     ForeignKey('user.user_id',
                                ondelete='CASCADE', onupdate='CASCADE'),
                     primary_key=True)
    # title of site
    title = Column(Unicode(255))
    # title of site
    brief = Column(Unicode(255))
    # description of site
    description = Column(UnicodeText(4096))
    # how many page visited
    visited = Column(Integer, default=0)
    # how many listener listened
    listened = Column(Integer, default=0)
    # language of this site
    language = Column(Unicode(16), index=True)
    # location of this site
    location = Column('location', Unicode(16), index=True)
    # is this a public radio site
    public = Column(Boolean(), nullable=False, default=True, index=True)
    # does this site have image
    has_image = Column(Boolean(), nullable=False, default=False)
    # image name of this radio
    image_name = Column(Unicode(64), index=True)
    # chatroom ACL setting, can be one of 0=OPEN, 1=MEMBER, 2=CLOSED
    chatroom_acl = Column(Integer, nullable=False, default=0)
    # audience country limitation, 0=include, 1=exclude
    country_limit = Column(Integer, nullable=False, default=1)

    # radio ACL setting, can be one of 0=OPEN, 1=MEMBER, 2=FRIENDS, 3=PRIVATE
    # radio_acl = Column(Integer, nullable=False, default=0)

    # enable password protection or not
    password_enable = Column(Boolean(), default=False)
    # password for user to access
    password = Column(Unicode(32))

    # sites associates with this tag
    site_tags = relation(
        'SiteTag',
        primaryjoin=user_id == SiteTag.user_id,
        foreign_keys=[SiteTag.user_id],
        cascade="all, delete-orphan",
        backref='site'
    )

    # sites associates with this tag
    tags = relation(
        'Tag',
        secondary=SiteTag.__table__,
        primaryjoin='Site.user_id == SiteTag.user_id',
        secondaryjoin='SiteTag.tag_id == Tag.id',
        backref='sites',
        viewonly=True
    )

    def __unicode__(self):
        return self.title


class Verification(DeclarativeBase):
    __tablename__ = 'verification'

    # the owner of verification
    user_id = Column(
        Integer,
        ForeignKey('user.user_id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    # type of verification
    type = Column(Unicode(16), primary_key=True)
    # code to verify
    code = Column(Unicode(255), nullable=False, index=True)
    # is this verification passed?
    passed = Column(Boolean, default=False, index=True)
    # extra data
    extra = Column(UnicodeText)
    # created date time
    created = Column(DateTime, default=now_func, index=True)


class Tag(DeclarativeBase):
    __tablename__ = 'tag'

    # id of tag
    id = Column(Integer, primary_key=True)

    # name of this tag
    name = Column(Unicode(32), index=True, unique=True, nullable=False)

    def __unicode__(self):
        return self.name


class Host(DeclarativeBase):
    __tablename__ = 'host'

    # id of host
    id = Column(Integer, primary_key=True)
    # ip address of host
    ip = Column(String(64), index=True, unique=True)
    # name of host
    name = Column(String(64), index=True)
    # is this host alive
    alive = Column(Boolean, index=True, nullable=False, default=False)
    # current loading of host
    loading = Column(Float, nullable=False, default=0)
    # when do the host serve gets on line
    online_time = Column(DateTime, nullable=False, default=now_func)
    # last updated time (for making sure the server is alive)
    last_updated = Column(DateTime, nullable=False, default=now_func)
    # created time
    created = Column(DateTime, nullable=False, default=now_func)
    # URL of supervisor's XMLRPC API
    supervisor_url = Column(String(128))


class Server(DeclarativeBase):
    __tablename__ = 'server'

    host_id = Column(
        Integer,
        ForeignKey('host.id', ondelete='CASCADE', onupdate='CASCADE'),
        index=True
    )
    id = Column(Integer, primary_key=True)
    # name of server
    name = Column(String(64), index=True, nullable=False)
    # type of server
    type = Column(String(64), index=True, nullable=False)
    # revision
    revision = Column(String(32), nullable=False)
    # pid of server process
    pid = Column(Integer, nullable=False)
    # maximum user of this server
    user_limit = Column(Integer, nullable=False, default=0)
    # current user count
    user_count = Column(Integer, nullable=False, default=0)
    # maximum resource on this server
    resource_limit = Column(Integer, nullable=False, default=0)
    # current resource count
    resource_count = Column(Integer, nullable=False, default=0)
    # is this server active
    active = Column(Boolean, index=True, nullable=False, default=False)
    # is this server one the line
    alive = Column(Boolean, index=True, nullable=False, default=False)
    # current loading of server
    loading = Column(Float, nullable=False, default=0)
    # inbound bandwidth rate (bytes per second)
    inbound_rate = Column(Float, nullable=False, default=0)
    # inbound bandwidth rate (bytes per second)
    outbound_rate = Column(Float, nullable=False, default=0)
    # when do the serve gets on line
    online_time = Column(DateTime, nullable=False, default=now_func)
    # last updated time (for making sure the server is alive)
    last_updated = Column(DateTime, nullable=False, default=now_func)
    # created time
    created = Column(DateTime, default=now_func)

    host = relation(
        "Host",
        backref="servers",
        primaryjoin="Host.id == Server.host_id"
    )

    # ports of this server
    ports = relation('Port', backref='server')

    __mapper_args__ = {'polymorphic_on': type}


class Port(DeclarativeBase):
    __tablename__ = 'port'

    server_id = Column(
        'server_id',
        Integer,
        ForeignKey('server.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    #: name of port
    name = Column(String(8), primary_key=True)

    #: address of port for accessing resource
    address = Column(String(64), nullable=False)


class Broadcast(Server):
    __tablename__ = 'broadcast'
    __mapper_args__ = {'polymorphic_identity': 'broadcast'}

    server_id = Column(
        'server_id',
        Integer,
        ForeignKey('server.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    on_airs = relation("OnAir", cascade="all, delete-orphan",
                       backref="broadcast")


class OnAir(DeclarativeBase):
    __tablename__ = 'on_air'

    # id of owner of radio
    user_id = Column(
        Integer,
        ForeignKey('user.user_id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    # broadcast server id
    server_id = Column(
        Integer,
        ForeignKey(
            'broadcast.server_id', ondelete='CASCADE', onupdate='CASCADE'),
        index=True,
        nullable=False
    )

    # when do the radio gets on air
    online_time = Column(DateTime, default=now_func)

    connections = relation(
        "ProxyConnection",
        backref="on_air",
        cascade="all, delete-orphan",
        primaryjoin="OnAir.user_id == ProxyConnection.user_id"
    )


class Proxy(Server):
    __tablename__ = 'proxy'
    __mapper_args__ = {'polymorphic_identity': 'proxy'}

    server_id = Column(
        'server_id',
        Integer,
        ForeignKey('server.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    connections = relation(
        "ProxyConnection",
        cascade="all, delete-orphan",
        backref="proxy"
    )


class ProxyConnection(DeclarativeBase):
    __tablename__ = 'proxy_connection'

    # proxy server id
    server_id = Column(
        Integer,
        ForeignKey('proxy.server_id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    # the owner user's id
    user_id = Column(
        Integer,
        ForeignKey('on_air.user_id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    # count of listeners
    listener = Column(Integer, nullable=False, default=0)


class Audio(DeclarativeBase):
    __tablename__ = 'audio'

    # unique id of audio file of audio
    id = Column(String(32), primary_key=True)

    # the owner of audio
    user_id = Column(
        Integer,
        ForeignKey('user.user_id', ondelete='CASCADE', onupdate='CASCADE'),
        index=True,
        nullable=False
    )

    #: filename of audio object in storage
    filename = Column(Unicode(128), nullable=False, index=True)

    #: what method did we use to create this file?
    #: could be (0=server record, 1=upload)
    create_method = Column(Integer, nullable=False)

    #: read permission
    #: could be (0=public, 1=friend only, 2=private)
    read_permission = Column(Integer, nullable=False)

    #: size of audio file
    size = Column(Integer, nullable=False)

    #: listened count
    listened = Column(Integer, nullable=False)

    #: title of audio file
    title = Column(Unicode(128))

    #: brief of this audio file
    brief = Column(UnicodeText(1024))

    #: created date of audio
    created = Column(DateTime, default=now_func)


class CountryLimit(DeclarativeBase):
    __tablename__ = 'country_limit'

    # unique id of audio file of audio
    id = Column(Integer, primary_key=True)

    # the owner of country list
    user_id = Column(
        Integer,
        ForeignKey('user.user_id', ondelete='CASCADE', onupdate='CASCADE'),
        index=True,
        nullable=True
    )

    #: country code
    code = Column(String(2), nullable=False, index=True)
