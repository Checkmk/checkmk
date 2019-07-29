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

    def __init__(self, resource, uri_end, tenant, client, secret):
        context = adal.AuthenticationContext('%s/%s' % (RestApiClient.AUTHORITY, tenant))
        token = context.acquire_token_with_client_credentials(resource, client, secret)

        self._ratelimit = float('Inf')
        self._base_url = resource + uri_end
        self._headers = {
            'Authorization': 'Bearer %s' % token['accessToken'],
            'Content-Type': 'application/json',
        }

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

    def get(self, uri_end, key=None, params=None):
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


class ManagementRestApi(object):
    def __init__(self, client):
        self.client = client

    def resourcegroups(self):
        return self.client.get('resourcegroups', key='value', params={'api-version': '2019-05-01'})

    def resources(self):
        return self.client.get('resources', key='value', params={'api-version': '2019-05-01'})

    def vmview(self, group, name):
        temp = 'resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s/instanceView'
        return self.client.get(temp % (group, name), params={'api-version': '2018-06-01'})

    def usagedetails(self):
        return self.client.get('providers/Microsoft.Consumption/usageDetails',
                               key='value',
                               params={'api-version': '2019-01-01'})

    def metrics(self, resource_id, **params):
        url = resource_id.split('/', 3)[-1] + "/providers/microsoft.insights/metrics"
        params['api-version'] = '2018-01-01'
        return self.client.get(url, key='value', params=params)
