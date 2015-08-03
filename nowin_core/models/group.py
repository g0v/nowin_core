import logging

from nowin_core.database import tables


class GroupModel(object):

    """Group data model

    """

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_group_by_id(self, group_id):
        """Get group by group id

        """
        group = self.session.query(tables.Group).get(int(group_id))
        return group

    def get_group_by_name(self, group_name):
        """Get a group by name

        """
        group = self.session \
            .query(tables.Group) \
            .filter_by(group_name=unicode(group_name)) \
            .first()
        return group

    def get_groups(self):
        """Get groups

        """
        query = self.session.query(tables.Group)
        return query

    def create_group(
        self,
        group_name,
        display_name=None,
    ):
        """Create a new group and return its id

        """
        group = tables.Group(
            group_name=unicode(group_name),
            display_name=unicode(
                display_name) if display_name is not None else None,
            created=tables.now_func()
        )
        self.session.add(group)
        # flush the change, so we can get real user id
        self.session.flush()
        assert group.group_id is not None, 'Group id should not be none here'
        group_id = group.group_id

        self.logger.info('Create group %s', group_name)
        return group_id

    def update_group(self, group_id, **kwargs):
        """Update attributes of a group

        """
        group = self.get_group_by_id(group_id)
        if group is None:
            raise KeyError
        if 'display_name' in kwargs:
            group.display_name = kwargs['display_name']
        if 'group_name' in kwargs:
            group.group_name = kwargs['group_name']
        self.session.add(group)

    def update_permissions(self, group_id, permission_ids):
        """Update permissions of this group

        """
        group = self.get_group_by_id(group_id)
        new_permissions = self.session \
            .query(tables.Permission) \
            .filter(tables.Permission.permission_id.in_(permission_ids))
        group.permissions = new_permissions.all()
        self.session.flush()
