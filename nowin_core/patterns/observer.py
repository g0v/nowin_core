class SubscribeID(object):

    def __init__(self, subject, sid):
        self.subject = subject
        self.sid = sid

    def unsubscribe(self):
        self.subject.unsubscribe(self.sid)


class Subject(object):

    """Object presents subject of observer pattern

    """

    def __init__(self):
        self.observers = {}
        self._sn = 0

    def subscribe(self, observer):
        """Subscribe an observer to this subject and return a subscription id

        """
        sid = self._sn
        self.observers[sid] = observer
        self._sn += 1
        return SubscribeID(self, sid)

    def unsubscribe(self, sid):
        """Disconnect an observer from this subject

        """
        assert sid in self.observers, \
            "Can't disconnect a observer does not connected to subject"
        del self.observers[sid]

    def __call__(self, *args, **kwargs):
        """Notify all observers which observe this subject

        """
        for observer in list(self.observers.itervalues()):
            observer(*args, **kwargs)
