import logging

from twisted.application import service
from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred


class StopOnErrorService(service.Service):

    """This service is for starting another service, if anything goes wrong
    when starting the service, it will stop whole server

    """

    def __init__(self, service, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.service = service

    def handleError(self, error):
        self.logger.fatal('Failed to start service %s', self.service)
        self.logger.exception(error)
        # use callFromThread here because we need to give reactor chacne to
        # start up, otherwise call reactor.stop directly would cause error,
        # because it is not running yet
        reactor.callFromThread(reactor.stop)

    def startService(self):
        d = maybeDeferred(self.service.startService)
        d.addErrback(self.handleError)
        return d
