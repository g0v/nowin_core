import logging

from nowin_core import signals
from nowin_core import utils
from nowin_core.database import tables


class AuthError(Exception):

    """Authentication error

    """


class BadPassword(AuthError):

    """Raised when user tries to authenticate with wrong password

    """


class UserNotExist(AuthError):

    """Raised when user tries to authenticate with a non-exist user

    """


class UserNotActived(AuthError):

    """Raised when user tries to authenticate when not activated

    """


class FollowingError(Exception):

    """Following model error

    """


class RelationShipExist(FollowingError):

    """Relation already exist

    """


class RelationShipNotExist(FollowingError):

    """Relation does not exist

    """


class SelfRelationError(FollowingError):

    """Cannot create relationship to self

    """


class UserModel(object):

    """User data model

    """

    # gender types
    GENDER_FEMALE = 0
    GENDER_MALE = 1
    GENDER_OTHER = 2

    # blood types
    BLOOD_TYPE_A = 0
    BLOOD_TYPE_B = 1
    BLOOD_TYPE_AB = 2
    BLOOD_TYPE_O = 3

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_user_by_name(self, user_name):
        """Get user by name

        """
        user = self.session \
            .query(tables.User) \
            .filter_by(user_name=unicode(user_name)) \
            .first()
        return user

    def get_user_by_id(self, user_id):
        """Get user by ID

        """
        user = self.session.query(tables.User).get(int(user_id))
        return user

    def get_users_by_id(self, user_ids, follow_list_order=False):
        """Get users by ID list

        if follow_list_order is true, the order will be returned as the order
        of user_ids

        """
        User = tables.User
        users = self.session.query(User) \
            .filter(User.user_id.in_(user_ids))
        if follow_list_order:
            pass
        return users

    def get_user_by_email(self, email):
        """Get user by email

        """
        user = self.session \
            .query(tables.User) \
            .filter_by(email=unicode(email)) \
            .first()
        return user

    def get_users_by_enable(self, enable):
        """Get users by enable status

        """
        users = self.session \
            .query(tables.User) \
            .filter_by(enable=enable)
        return users

    def query_user(self, user_id=None, user_name=None, email=None):
        """Query user by different conditions

        """
        query = self.session.query(tables.User)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        if user_name is not None:
            query = query.filter_by(user_name=user_name)
        if email is not None:
            query = query.filter_by(email=email)
        return query.first()

    def get_verification(self, user_id, type, code=None):
        """Get a verification

        """
        Verification = tables.Verification
        query = self.session \
            .query(Verification) \
            .filter(Verification.user_id == user_id) \
            .filter(Verification.type == type)
        if code is not None:
            query = query.filter(Verification.code == code)
        return query.first()

    def create_verification(self, user_id, type, code):
        """Create a verification

        """
        Verification = tables.Verification
        verify = Verification(user_id=user_id,
                              type=type,
                              code=code,
                              created=tables.now_func())
        self.session.add(verify)
        self.session.flush()

    def remove_verification(self, user_id, type, code=None):
        """Remove a verification

        """
        verify = self.getVerification(user_id, type, code)
        if verify is not None:
            self.session.delete(verify)
        self.session.flush()

    def create_user(
        self,
        user_name,
        email,
        display_name,
        password
    ):
        """Create a new user and return verification

        """
        user_name = user_name.lower()
        email = email.lower()
        # create user
        user = tables.User(
            user_name=unicode(user_name),
            email=unicode(email),
            display_name=unicode(display_name),
            password=password,
            created=tables.now_func()
        )
        # create verification
        code = utils.generateRandomCode()
        verification = tables.Verification(
            user=user,
            type=u'create_user',
            code=code,
            created=tables.now_func()
        )
        self.session.add(user)
        self.session.add(verification)
        # flush the change, so we can get real user id
        self.session.flush()
        assert user.user_id is not None, 'User id should not be none here'
        user_id = user.user_id

        signals.user_created_event(user_id)

        self.session.flush()

        self.logger.info('Create user %s with verification %s',
                         user, verification)
        return user_id

    def activate_user(self, user_id, site_title, site_location):
        """Activate user account

        """
        verification = self.session \
            .query(tables.Verification) \
            .filter_by(user_id=user_id, type=u'create_user')\
            .first()

        assert verification is not None, \
            'cannot find verification of %s' % user_id
        assert not verification.passed, \
            'user %s has already been activated' % user_id

        user = verification.user
        site = tables.Site(title=unicode(site_title),
                           location=unicode(site_location).upper())
        user.site = site
        verification.passed = True
        self.session.add(verification)
        self.session.add(site)
        self.session.flush()

        signals.user_activated_event(user_id)

        self.session.flush()

        self.logger.info('Activated user %s with verification %s',
                         user_id, verification)

    def authenticate_user(self, name_or_email, password):
        """Authenticate user by user_name of email and password. If the user
        pass the authentication, return user_id, otherwise, raise error

        """
        from sqlalchemy.sql.expression import or_
        User = tables.User
        user = self.session.query(User) \
            .filter(or_(User.user_name == name_or_email,
                        User.email == name_or_email)) \
            .first()
        if user is None:
            # maybe it's case problem, although we enforce lower case to
            # user name and email now, but it seems there is still some
            # accounts have id in different cases, so that's why we do the
            # user query twice
            name_or_email = name_or_email.lower()
            user = self.session.query(User) \
                .filter(or_(User.user_name == name_or_email,
                            User.email == name_or_email)) \
                .first()
            if user is None:
                raise UserNotExist('User %s does not exist' % name_or_email)
        if not user.validate_password(password):
            raise BadPassword('Bad password')
        if not user.active:
            raise UserNotActived('User %s is not activated' % user.user_name)
        return user.user_id

    def update_profile(self, user_id, **kwargs):
        """Update profile of an user

        """
        user = self.get_user_by_id(user_id)
        if 'display_name' in kwargs:
            user.display_name = kwargs['display_name']
        if 'profile' in kwargs:
            user.profile = kwargs['profile']
        if 'birthday' in kwargs:
            user.birthday = kwargs['birthday']
        if 'gender' in kwargs:
            user.gender = kwargs['gender']
        if 'blood_type' in kwargs:
            user.blood_type = kwargs['blood_type']
        if 'website_link' in kwargs:
            user.website_link = kwargs['website_link']
        if 'image_name' in kwargs:
            user.image_name = kwargs['image_name']
        self.session.add(user)
        self.session.flush()

    def update_user_enable(self, user_id, enable):
        """Update enable status of an user

        """
        user = self.get_user_by_id(user_id)
        self.logger.info('Set user %r enable from %r to %r',
                         user.user_name, user.enable, enable)
        user.enable = enable
        self.session.add(user)
        self.session.flush()

    def update_password(self, user_id, password):
        """Update password of an user

        """
        user = self.get_user_by_id(user_id)
        user.password = password
        self.session.add(user)
        self.session.flush()

    def update_site(
        self,
        user_id,
        **kwargs
    ):
        Site = tables.Site
        Tag = tables.Tag
        SiteTag = tables.SiteTag

        site = self.session.query(Site).filter_by(user_id=user_id).first()

        if 'title' in kwargs:
            site.title = unicode(kwargs['title'])
        if 'brief' in kwargs:
            site.brief = unicode(kwargs['brief'])
        if 'description' in kwargs:
            site.description = unicode(kwargs['description'])
        if 'public' in kwargs:
            site.public = kwargs['public']
        if 'location' in kwargs:
            site.location = kwargs['location'].upper()
        if 'image_name' in kwargs:
            site.image_name = kwargs['image_name']
        if 'password' in kwargs:
            site.password = kwargs['password']
        if 'password_enable' in kwargs:
            site.password_enable = kwargs['password_enable']

        if 'tags' in kwargs:
            new_tags = set(map(unicode, kwargs['tags']))
            old_tags = set([tag.name for tag in site.tags])
            remain_tag = new_tags & old_tags
            to_delete = old_tags - remain_tag
            to_add = new_tags - remain_tag

            for tag_name in to_delete:
                tag = self.session \
                    .query(Tag) \
                    .filter(Tag.name == tag_name) \
                    .first()
                site_tag = self.session \
                    .query(SiteTag) \
                    .filter(SiteTag.user_id == site.user.user_id) \
                    .filter(SiteTag.tag_id == tag.id) \
                    .first()
                self.session.delete(site_tag)

            for tag_name in to_add:
                tag = self.session \
                    .query(Tag) \
                    .filter(Tag.name == tag_name) \
                    .first()
                if tag is None:
                    tag = Tag(name=tag_name)
                    self.session.add(tag)
                self.session.flush()

                site_tag = SiteTag(user_id=site.user_id,
                                   tag_id=tag.id)
                self.session.add(site_tag)
        self.session.add(site)
        self.session.flush()

    def update_groups(self, user_id, group_ids):
        """Update groups of this user

        """
        user = self.get_user_by_id(user_id)
        new_groups = self.session \
            .query(tables.Group) \
            .filter(tables.Group.group_id.in_(group_ids))
        user.groups = new_groups.all()
        self.session.flush()


class FollowingModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_followings(self, user_id):
        """Get following id list of an user

        """
        ids = self.session.query(tables.Following.target_id) \
            .filter_by(owner_id=user_id)
        return map(lambda item: item[0], ids.all())

    def add_following(self, owner_id, target_id):
        """Add following relationship from an user to another

        """
        if owner_id == target_id:
            raise SelfRelationError('Cannot follow self')
        following = self.session.query(tables.Following) \
            .get((owner_id, target_id))
        if following is not None:
            raise RelationShipExist('Relationship from %s to %s already exist'
                                    % (owner_id, target_id))
        following = tables.Following(owner_id=owner_id, target_id=target_id)
        self.session.add(following)
        self.session.flush()

    def remove_following(self, owner_id, target_id):
        """Remaove a following relationship

        """
        following = self.session.query(tables.Following) \
            .get((owner_id, target_id))
        if following is None:
            raise RelationShipNotExist(
                'Relationship from %s to %s does not exist'
                % (owner_id, target_id)
            )
        self.session.delete(following)
        self.session.flush()

    def get_following_state(self, owner_id, target_id):
        """Get following state between two user, if there is no following
        relationship between owner and target, None is returned. If there
        is following relationship between owner and target, the result could be

        1:
            owner -> target
        2:
            owner <- target
        3:
            owner <-> target

        """
        owner2target = self.session.query(tables.Following) \
            .get((owner_id, target_id))
        target2owner = self.session.query(tables.Following) \
            .get((target_id, owner_id))
        if owner2target and target2owner:
            return 3
        if owner2target:
            return 1
        if target2owner:
            return 2
        return None


class PrivacyModel(object):

    # privacy options
    OPTION_PUBLIC = 0
    OPTION_FIRENDS_ONLY = 1
    OPTION_HIDDEN = 2

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def set_options(self, user_id, **kwargs):
        """Set privacy options of an use_add

        """
        options = self.get_options(user_id)
        for key, value in kwargs.iteritems():
            # update
            if key in options:
                op = self.session.query(tables.PrivacyOption) \
                    .get((user_id, key))
                op.value = value
                self.session.add(op)
            # add
            else:
                op = tables.PrivacyOption(
                    user_id=user_id,
                    name=key,
                    value=value
                )
                self.session.add(op)
        self.session.flush()

    def get_options(self, user_id):
        """Get privacy options of an user, result will be a dictionary

        """
        options = self.session.query(tables.PrivacyOption) \
            .filter_by(user_id=user_id) \
            .all()
        result = {}
        for op in options:
            result[op.name] = op.value
        return result

    def get_user_view(self, user, viewer_id):
        """Get allowed view of user by viewer

        """
        result = dict(
            user_id=user.user_id,
            display_name=user.display_name,
            profile=user.profile,
            birthday=user.birthday,
            gender=user.gender,
            blood_type=user.blood_type,
            website_link=user.website_link,
        )
        options = self.get_options(user.user_id)

        def test_op(name):
            return options.get(name, self.OPTION_PUBLIC) != self.OPTION_PUBLIC

        op_list = [
            ('user_birthday', 'birthday'),
            ('user_gender', 'gender'),
            ('user_blood_type', 'blood_type'),
            ('user_website_link', 'website_link'),
        ]
        for opname, attrname in op_list:
            if test_op(opname):
                result[attrname] = None
        return result
