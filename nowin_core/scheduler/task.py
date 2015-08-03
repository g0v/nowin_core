import functools
import logging


def log_exception(logger=None):
    """Log exceptions raised in function

    """
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @functools.wraps(func)
        def callee(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception:
                logger.info('Catch error', exc_info=True)
        return callee
    return decorator


class Task(object):

    def __init__(self, scheduler, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler

    def start(self):
        pass

    def stop(self):
        pass


class LoopingCall(Task):

    """Periodically called function

    """

    def __init__(
        self,
        scheduler,
        period,
        target,
        args=tuple(),
        kwargs={},
        logger=None
    ):
        Task.__init__(self, scheduler, logger)

        #: period in seconds to execute task
        self.period = period
        #: target function to be called
        self.target = target
        #: arguments
        self.args = args
        # L kwargs
        self.kwargs = kwargs

        self._event = None

    def start(self):
        """Start the task

        """
        self.run()

    def stop(self):
        assert self._event is not None
        self.scheduler.cancel(self._event)

    def run(self):
        """Run the task

        """
        func = log_exception(self.logger)(self.target)
        func(*self.args, **self.kwargs)
        self._event = self.scheduler.enter(self.period, 1, self.run, ())
