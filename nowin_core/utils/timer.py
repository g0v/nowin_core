import functools
import logging
import time


def timer(func=None, now_func=None, logger=None):
    """Decorator for write duration time of a function call to logger

    For example, to log calling time of a function foo, we can write

    ..

        @timer
        def foo():
            pass

    The default logger is timer.<function_name>, to use a customer logger,
    we can write

    ..

        @timer(logger=my_logger)
        def bar():
            pass

    """
    if now_func is None:
        now_func = time.time

    def decorator(func):
        @functools.wraps(func)
        def callee(*args, **kwargs):
            l = logger
            if l is None:
                l = logging.getLogger('timer.%s' % func.__name__)
            l.debug(
                'Start function call to %s(*%s, **%s)',
                func.__name__, args, kwargs
            )
            begin = now_func()
            result = func(*args, **kwargs)
            l.debug(
                'Stop function call to %s(*%s, **%s)',
                func.__name__,
                args,
                kwargs
            )
            elapsed = now_func() - begin
            l.info(
                'Call to %s costs %s seconds',
                func.__name__,
                elapsed
            )
            return result
        return callee
    if func is not None:
        return decorator(func)
    return decorator

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    @timer
    def foo(arg1, arg2):
        time.sleep(2)
        return '123', arg1, arg2
    print foo('test', 123)

    @timer(logger=logging.getLogger('my_logger'))
    def bar():
        time.sleep(1)
        return '456'
    print bar()
