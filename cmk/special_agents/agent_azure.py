#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import logging
import adal  # type: ignore
import requests

LOGGER = logging.getLogger()  # root logger for now


class ApiError(RuntimeError):
    pass


class RestApiClient(object):

    AUTHORITY = 'https://login.microsoftonline.com'
    RESOURCE = 'https://management.azure.com'

    def __init__(self):
        self._ratelimit = float('Inf')
        self._base_url = None
        self._headers = {}

    def login(self, tenant, client, secret, subscription):
        context = adal.AuthenticationContext('%s/%s' % (RestApiClient.AUTHORITY, tenant))
        token = context.acquire_token_with_client_credentials(RestApiClient.RESOURCE, client,
                                                              secret)
        self._headers.update({
            'Authorization': 'Bearer %s' % token['accessToken'],
            'Content-Type': 'application/json',
        })
        self._base_url = '%s/subscriptions/%s/' % (RestApiClient.RESOURCE, subscription)

    @property
    def ratelimit(self):
        if isinstance(self._ratelimit, int):
            return self._ratelimit
        return None

    def _update_ratelimit(self, response):
        try:
            new_value = int(response.headers['x-ms-ratelimit-remaining-subscription-reads'])
        except (KeyError, ValueError, TypeError):
            return
        self._ratelimit = min(self._ratelimit, new_value)

    def _get(self, uri_end, key=None, params=None):
        request_url = self._base_url + uri_end
        response = requests.get(request_url, params=params, headers=self._headers)
        self._update_ratelimit(response)
        json_data = response.json()
        LOGGER.debug('response: %r', json_data)

        if key is None:
            return json_data
        try:
            return json_data[key]
        except KeyError:
            error = json_data.get('error', json_data)
            raise ApiError(error.get('message', json_data))

    def resourcegroups(self):
        return self._get('resourcegroups', key='value', params={'api-version': '2019-05-01'})

    def resources(self):
        return self._get('resources', key='value', params={'api-version': '2019-05-01'})

    def vmview(self, group, name):
        temp = 'resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s/instanceView'
        return self._get(temp % (group, name), params={'api-version': '2018-06-01'})

    def usagedetails(self):
        return self._get('providers/Microsoft.Consumption/usageDetails',
                         key='value',
                         params={'api-version': '2019-01-01'})

    def metrics(self, resource_id, **params):
        url = resource_id.split('/', 3)[-1] + "/providers/microsoft.insights/metrics"
        params['api-version'] = '2018-01-01'
        return self._get(url, key='value', params=params)


rest_client = RestApiClient()
