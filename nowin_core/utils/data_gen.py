import logging
import os
import time


class DataGenerator(object):

    """Dummy data generator

    """

    def __init__(self, kbps, now_func=None, data_func=None, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        #: kbps for generating data
        self.kbps = kbps
        #: how many bytes per kilobit
        self.kbit_bytes = 1000 / 8.0
        #: function for returning current time in seconds.
        self.now_func = now_func
        if self.now_func is None:
            self.now_func = time.time
        #: function for getting data, called with argument (data size)
        self.data_func = data_func
        if self.data_func is None:
            self.data_func = os.urandom
        #: last update time
        self.last_update = None

    def getData(self):
        """Get data,

        First call to this function the return value will be an empty string

        """
        now = self.now_func()
        if self.last_update is None:
            self.last_update = now
            return ''
        elapsed = now - self.last_update
        if elapsed == 0:
            return ''
        data = self.data_func(int(self.kbps * self.kbit_bytes * elapsed))
        self.last_update = now
        return data
