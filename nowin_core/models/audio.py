import logging

from nowin_core.database import tables


class AudioModel(object):

    """Audio model

    """

    #: audio created by server recording
    CREATE_METHOD_SERVER_RECORD = 0
    #: audio created by uploadding
    CREATE_METHOD_UPLOAD = 1

    CREATE_METHODS = set([CREATE_METHOD_SERVER_RECORD, CREATE_METHOD_UPLOAD])

    #: public permission
    PERMISSION_PUBLIC = 0
    #: limited to friends only
    PERMISSION_FRIEND_ONLY = 1
    #: private
    PERMISSION_PRIVATE = 2

    PERMISSIONS = set([PERMISSION_PUBLIC, PERMISSION_FRIEND_ONLY,
                       PERMISSION_PRIVATE])

    def __init__(self, session, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.session = session

    def get_audio_by_id(self, audio_id):
        """Get and audio by ID

        """
        return self.session.query(tables.Audio).get(audio_id)

    def create_audio(
        self,
        audio_id,
        user_id,
        filename,
        create_method,
        read_permission,
        size,
        title=None,
        brief=None,
        listened=0,
        created=None
    ):
        """Create an audio file

        """
        if create_method not in self.CREATE_METHODS:
            raise ValueError('Invalid create_method %s' % create_method)
        if read_permission not in self.PERMISSIONS:
            raise ValueError('Invalid read_permission %s' % read_permission)
        audio = tables.Audio(
            id=audio_id,
            user_id=user_id,
            filename=filename,
            create_method=create_method,
            read_permission=read_permission,
            size=size
        )
        if title is not None:
            audio.title = title
        if brief is not None:
            audio.brief = brief
        if listened is not None:
            audio.listened = listened
        if created is not None:
            audio.created = created
        self.session.add(audio)
        self.session.flush()

    def update_audio(self, audio_id, **kwargs):
        """Update an audio

        """
        if (
            'create_method' in kwargs and
            kwargs['create_method'] not in self.CREATE_METHODS
        ):
            raise ValueError('Invalid create_method %s' %
                             kwargs['create_method'])

        if (
            'read_permission' in kwargs and
            kwargs['read_permission'] not in self.PERMISSIONS
        ):
            raise ValueError('Invalid read_permission %s' %
                             kwargs['read_permission'])

        audio = self.get_audio_by_id(audio_id)
        if 'create_method' in kwargs:
            audio.create_method = kwargs['create_method']
        if 'read_permission' in kwargs:
            audio.read_permission = kwargs['read_permission']
        if 'filename' in kwargs:
            audio.filename = kwargs['filename']
        if 'size' in kwargs:
            audio.size = kwargs['size']
        if 'title' in kwargs:
            audio.title = kwargs['title']
        if 'brief' in kwargs:
            audio.brief = kwargs['brief']
        if 'listened' in kwargs:
            audio.listened = kwargs['listened']
        self.session.add(audio)
        self.session.flush()

    def remove_audio(self, audio_id):
        """Remove an audio

        """
        audio = self.get_audio_by_id(audio_id)
        self.session.delete(audio)
        self.session.flush()

    def get_space_usage(self, user_id):
        """Get space usage of user

        """
        from sqlalchemy.sql.expression import func
        # 100 MB basic space
        basic = 100 * 1024 * 1024
        # TODO: sum space of user here
        used = self.session \
            .query(func.ifnull(func.sum(tables.Audio.size), 0)) \
            .filter_by(user_id=user_id) \
            .scalar()
        return dict(total=basic, used=used)
