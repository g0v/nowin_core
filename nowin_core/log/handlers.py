# -*- coding: utf-8
import json
import logging
import Queue
import socket
import sys
import threading
import traceback
import urllib
import warnings

import httplib2

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class WorkerThread(threading.Thread):

    def __init__(self, debug, debug_stream):
        threading.Thread.__init__(self, name='HTTP-Handler-Thread')
        # exit when python is closed
        self.daemon = True
        self.queue = Queue.Queue()
        self.debug = debug
        self.debug_stream = debug_stream

    def call_in_thread(self, func, *args, **kwargs):
        """Put a function call to run in thread

        """
        self.queue.put((func, args, kwargs))

    def run(self):
        if self.debug:
            print >> self.debug_stream, 'Start thread'
        try:
            while True:
                job = self.queue.get()
                if job is None:
                    break
                if self.debug:
                    print >> self.debug_stream, 'Run job', job
                func, args, kwargs = job
                try:
                    func(*args, **kwargs)
                except (KeyboardInterrupt, SystemExit):
                    break
                except Exception:
                    if self.debug:
                        print 'Failed to execute'
        except (KeyboardInterrupt, SystemExit):
            return


class HTTPHandler(logging.Handler):

    """Handler for writing log records to central log

    url is the URL of central log write API
    app_name is the name of this application

    """

    def __init__(
        self,
        url,
        api_key,
        app_name,
        level=logging.NOTSET,
        hostname='_default_',
        threading=True,
        join_timeout=3,
        debug_file=None,
        debug=False
    ):
        logging.Handler.__init__(self)
        self.app_name = app_name
        self.api_key = api_key
        self.url = url
        self.threading = threading
        self.join_timeout = join_timeout
        self.debug_file = debug_file
        self.debug = debug

        if self.debug_file is None:
            self._debug_stream = sys.stderr
        else:
            self._debug_stream = open(self.debug_file, 'at')

        if hostname == '_default_':
            self.hostname = socket.gethostname()

        if self.threading:
            self._queue = []
            self._thread = WorkerThread(debug=self.debug,
                                        debug_stream=self._debug_stream)
            self._thread.start()

    def flush(self):
        if self.threading:
            self._join_thread()

    def _join_thread(self):
        self._thread.join(self.join_timeout)

    def _add_record(self, record):
        """Add a record, might send the record directly

        """
        if self.threading:
            self._queue.append(record)
            self._thread.call_in_thread(self._send_queue)
        else:
            self._send_records([record])

    def _send_queue(self):
        """Send records in queue

        """
        if not self._queue:
            return
        try:
            self.acquire()
            records = self._queue
            self._queue = []
        finally:
            self.release()
        if self.debug:
            print >> self._debug_stream, \
                'Current queue site %s' % len(self._queue)
        self._send_records(records)

    def _send_records(self, records):
        """Send records through HTTP

        """
        body = json.dumps(records)

        h = httplib2.Http()
        query = urllib.urlencode(dict(api_key=self.api_key))
        url = self.url + '?' + query
        if self.debug:
            print >> self._debug_stream, 'Send request to %s' % url
            print >> self._debug_stream, 'Body: %r' % body
        reps, content = h.request(url, 'POST', body=body)
        if self.debug:
            print >> self._debug_stream, 'Get response %r' % reps
            print >> self._debug_stream, 'Get content %r' % content

        # DO some check here, make sure we did send the records
        if reps['status'] != '200':
            if self.debug:
                print >> self._debug_stream, 'Got unexpected code', reps[
                    'status']
            msg = 'Failed to send HTTP log record with response code %s' %  \
                reps['status']
            warnings.warn(msg, RuntimeWarning)
            return
        result = json.loads(content)
        if result['code'] != 'ok':
            if self.debug:
                print >> self._debug_stream, 'Failed to submit request'
            msg = 'Failed to send HTTP log record with result %r' %  \
                result
            warnings.warn(msg, RuntimeWarning)
            return

    def emit(self, record):
        try:
            msg = record.getMessage()
            r = dict(
                app_name=self.app_name,
                hostname=self.hostname,
                name=record.name,
                levelname=record.levelname,
                message=msg,
                created=record.created,
            )
            if record.exc_info is not None:
                dump = StringIO.StringIO()
                traceback.print_exception(*record.exc_info, file=dump)
                r['traceback'] = dump.getvalue()
            self._add_record(r)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    handler = HTTPHandler(
        url='http://127.0.0.1:4000/api/write_log',
        api_key='test_key',
        app_name='test_app',
        threading=False,
        debug=0,
        debug_file='debug.txt'
    )
    logger.addHandler(handler)

    logger.info('test123 %s', 'txt')
    try:
        raise Exception('test')
    except:
        logger.fatal('test', exc_info=True)
    logger.info('123')
