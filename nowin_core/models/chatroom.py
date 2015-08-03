import logging

from nowin_core import signals
from nowin_core.database import tables
from nowin_core.models.user import UserModel


class DuplicateError(Exception):

    """Duplicate blocking error

    """


class NotExistError(Exception):

    """User does not exist error

    """


class SelfBlockError(Exception):

    """Try to block self error

    """


class ChatroomModel(object):

    """Chat-room model model

    """

    #: anyone can join chat-room
    ACL_OPEN = 0
    #: only member can join chat-room
    ACL_MEMBER = 1
    #: chat-room is disabled
    ACL_CLOSED = 2

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_settings(self, user_id):
        """Get settings of chat-room

        """
        radio = self.session.query(tables.Site) \
            .filter_by(user_id=user_id) \
            .first()
        if radio is None:
            raise NotExistError('Radio %s does not exist' % user_id)
        return dict(acl=radio.chatroom_acl)

    def update_settings(self, user_id, acl=None):
        """Update chat-room settings

        """
        radio = self.session.query(tables.Site) \
            .filter_by(user_id=user_id) \
            .first()
        if radio is None:
            raise NotExistError('Radio %s does not exist' % user_id)

        if acl is not None:
            assert acl in [0, 1, 2], "ACL can only be 1, 2 or 3"
            radio.chatroom_acl = acl

        self.session.add(radio)
        self.session.flush()

        signals.chatroom_setting_changed(user_id)

    def iter_blocked_list(self, owner_id):
        """Get id list of blocked users in a chat-room as an iterator

        """
        query = self.session.query(tables.Blocking) \
            .filter_by(owner_id=owner_id)
        for blocking in query:
            yield blocking.target_id

    def get_blocked_list(self, owner_id):
        """Get id list of blocked users in a chat-room

        """
        return list(self.iter_blocked_list(owner_id))

    def add_blocked_user(self, owner_id, target_id):
        """Add an user to blocked list in a chat-room as a list

        owner_id is the id of chat-room owner, and target_id is the target user
        to block

        """
        if owner_id == target_id:
            raise SelfBlockError("Self-blocking is not allowed")

        radio = self.session.query(tables.Site) \
            .filter_by(user_id=owner_id) \
            .first()
        if radio is None:
            raise NotExistError('Radio %s does not exist' % owner_id)

        user_model = UserModel(self.session)
        target_user = user_model.get_user_by_id(target_id)
        if target_user is None:
            raise NotExistError('Target user %s does not exist' % target_user)

        blocking = self.get_blocking(owner_id, target_id)
        if blocking is not None:
            raise DuplicateError('Duplicate block from %s to %s' %
                                 (owner_id, target_id))

        blocking = tables.Blocking(owner_id=owner_id, target_id=target_id)
        self.session.add(blocking)
        self.session.flush()

    def get_blocking(self, owner_id, target_id):
        """Get blocking object and return

        """
        blocking = self.session.query(tables.Blocking) \
            .filter_by(owner_id=owner_id, target_id=target_id) \
            .first()
        return blocking

    def remove_blocked_user(self, owner_id, target_id):
        """Remove an user from blocked list in a chat-room

        """
        blocking = self.get_blocking(owner_id, target_id)
        if blocking is None:
            raise NotExistError("Blocking from %s to %s does not exist" %
                                (owner_id, target_id))
        self.session.delete(blocking)
        self.session.flush()

    def check_permission(self, owner_id, guest_id):
        """Check can an user with guest_id access chat-room of
        user with owner_id?

        if the guest is joining anonymously, then the guest_id should be None
        """
        # TODO: check is the guest an administrator
        settings = self.get_settings(owner_id)
        acl = settings['acl']
        if acl == self.ACL_CLOSED:
            return False
        if acl == self.ACL_MEMBER:
            if guest_id is None:
                return False
            # make sure the guest user is activated
            user_model = UserModel(self.session)
            user = user_model.get_user_by_id(guest_id)
            if not user.active:
                return False
        blocking = self.get_blocking(owner_id, guest_id)
        return blocking is None
