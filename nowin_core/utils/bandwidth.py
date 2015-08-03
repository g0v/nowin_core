import logging
import time

from nowin_core.patterns import observer
from nowin_core.utils import convertBpsToKbps
from nowin_core.utils import convertBpsToMbps


class Bandwidth(object):

    """Object for calculating bandwidth

    """

    def __init__(self, time_func=None, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.time_func = time_func
        if self.time_func is None:
            self.time_func = time.time
        self._count = 0
        self._rate = 0
        self._last_count = 0
        self._last_time = None

        #: called when the bandwidth is calculated with args (new rate)
        self.update_event = observer.Subject()

    @property
    def byte_rate(self):
        """Bytes per seconds

        """
        return self._rate

    @property
    def mbps(self):
        """Million bits per seconds

        """
        return convertBpsToMbps(self._rate)

    @property
    def kbps(self):
        """kilobits per seconds

        """
        return convertBpsToKbps(self._rate)

    def increase(self, delta):
        """Increase byte count

        """
        self._count += delta

    def calculate(self):
        """Calculate bandwidth rate since last call

        """
        rate = 0.0
        now = self.time_func()

        # this is not first call
        if self._last_time is not None:
            # get delta
            count_delta = self._count - self._last_count
            time_delta = float(now - self._last_time)
            if time_delta:
                rate = count_delta / time_delta

        # update last record
        self._last_time = now
        self._last_count = self._count
        self._rate = rate
        self.update_event(rate)
        self.logger.debug('Bandwidth updated to %.1f Mbps', self.mbps)
