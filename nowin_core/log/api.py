import json
import logging
import urllib
import urlparse

import httplib2


class CentralLogAPIError(RuntimeError):

    """Error of central log API call

    """


class CentralLogAPI(object):

    def __init__(self, api_url, api_key, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.api_url = api_url
        self.api_key = api_key

    def read_records(
        self,
        offset=None,
        limit=None,
        levels=None,
        hosts=None,
        apps=None,
        channels=None,
        order_by=None,
        id_base=None
    ):
        """Read log records

        """
        h = httplib2.Http()

        url = urlparse.urljoin(self.api_url, 'read_log')
        query = dict(api_key=self.api_key)
        if offset is not None:
            query['offset'] = offset
        if limit is not None:
            query['limit'] = limit
        if levels is not None:
            query['levels'] = levels
        if hosts is not None:
            query['hosts'] = hosts
        if apps is not None:
            query['apps'] = apps
        if channels is not None:
            query['channels'] = channels
        if id_base is not None:
            query['id_base'] = id_base
        if order_by is not None:
            query['order_by'] = [','.join(order) for order in order_by]
        url += '?' + urllib.urlencode(query, True)

        reps, content = h.request(url, 'GET')
        if reps['status'] != '200':
            self.logger.error(
                'Failed to call central log API with HTTP code %s',
                reps['status']
            )
            msg = 'Failed to call central log API %s with status code %s' % (
                self.api_url, reps['status'])
            raise CentralLogAPIError(msg)

        result = json.loads(content)
        return result
