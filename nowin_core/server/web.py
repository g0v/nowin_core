import logging

from twisted.web import server


class HttpLogFile(object):

    def __init__(self, logger=None, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg.strip())

    def close(self):
        pass


class SiteWithLogger(server.Site):

    """A overrided version of Site, use our own logger rather than twistd's
    suck logging system

    """

    def __init__(
        self,
        resource,
        logger=None,
        logPath=None,
        timeout=60 * 60 * 12,
    ):
        server.Site.__init__(self, resource, logPath, timeout)
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def startFactory(self):
        server.Site.startFactory(self)
        self.logFile = HttpLogFile(self.logger)
