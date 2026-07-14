#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2026 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
import argparse

import requests, json
from pprint import pformat
from typing import List, Dict, Any, Literal
from pydantic import HttpUrl
from labelpicker_ng import LabelpickerConfig, Host, Labels, logger, CheckmkConfig


class CMKInstance:
    """
    Interact with checkmk instance
    """

    def __init__(
            self,
            config: CheckmkConfig,
    ):
        """
        Initializes the instance with the given configuration, prepares HTTP headers, and sets up the session
        for communication with the API.

        :param config: Configuration object containing Checkmk connection details such as username, password,
                       and API URL.
        :type config: LabelpickerConfig
        """
        self.headers = {
            "Content-Type": "application/json",
        }
        if not config.password:
            raise ValueError("API-Password cannot be None")

        self._session = requests.session()
        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["Accept"] = "application/json"
        self._session.headers["Authorization"] = f"Bearer {config.username} {config.password.get_secret_value()}"
        self.config: CheckmkConfig = config
        self._api_url: HttpUrl | None = config.api_url
        self.version: Dict[str, Any] | None = self.get_version()

    @staticmethod
    def _trans_resp(
            resp: requests.Response,
    ) -> tuple[dict, requests.Response]:
        """
        Transforms the given HTTP response into a tuple of parsed JSON data and the
        original response object.

        If the response body cannot be decoded as JSON, an empty dictionary is returned
        as the data, and an error is logged.

        :param resp: The HTTP response object received from a request.
        :type resp: requests.Response

        :return: A tuple containing the parsed JSON data (as a dictionary) and the
            original response object.
        :rtype: tuple[dict, requests.Response]
        """
        try:
            data = resp.json()
        except json.decoder.JSONDecodeError:
            data = {}
            logger.error(f"JSONDecodeError for data: \n{pformat(resp.text, indent=4)}")
        return data, resp

    def _request_url(
            self,
            method: Literal["GET", "POST", "PUT"],
            endpoint: str,
            data: dict | None = None,
            e_tag: str | None = None
    ) -> tuple[dict, requests.Response]:
        """
        Sends a request to a specified API endpoint using the provided HTTP method and optional
        data and ETag headers. Returns the parsed response along with the original response object.

        :param method: HTTP method for the request. Must be one of 'GET', 'POST', or 'PUT'.
        :param endpoint: The API endpoint to send the request to.
        :param data: (Optional) Dictionary containing data to be sent in the request body. Defaults to an empty dictionary.
        :param e_tag: (Optional) Value for the 'If-Match' header, typically used for conditional requests.
        :return: A tuple containing the parsed response as a dictionary and the original response object.
        """
        if data is None:
            data = {}

        headers = self.headers

        if e_tag is not None:
            headers["If-Match"] = e_tag

        url = f"{self._api_url}/{endpoint}"

        request_func = getattr(self._session, method.lower())

        return self._trans_resp(
            request_func(
                url,
                json=data,
                headers=headers,
                allow_redirects=False,
            )
        )

    def _get_url(
            self,
            endpoint: str,
            data: dict | None = None
    ) -> tuple[dict, requests.Response]:
        """
        Generates a GET request to a specified endpoint with optional data.

        The method constructs a request to the defined endpoint using the HTTP GET method
        and includes any optional data provided in the request. It returns the response
        of the request along with an additional data dictionary.

        :param endpoint: The specified API endpoint to make the GET request to.
        :type endpoint: str
        :param data: Optional dictionary containing data to be sent with the request.
        Defaults to None.
        :type data: dict | None
        :return: A tuple containing the response data as a dictionary and the
        response object.
        :rtype: tuple[dict, requests.Response]
        """
        if data is None:
            data = {}
        return self._request_url("GET", endpoint, data)

    def _put_url(
            self,
            endpoint: str,
            e_tag: str,
            data: dict | None = None,
    ) -> tuple[dict, requests.Response]:
        """
        Sends a PUT request to the specified endpoint with the provided data and ETag.

        This function is used to update resources at the specified endpoint. It ensures
        the data is sent along with the appropriate HTTP headers using the ETag for
        optimistic concurrency control. If no data is provided, an empty dictionary is
        sent as the request payload.

        :param endpoint: The API endpoint where the PUT request should be directed.
        :type endpoint: str
        :param e_tag: The ETag value used for updating the resource.
        :type e_tag: str
        :param data: The data payload to send with the PUT request. Defaults to None.
        :type data: dict | None
        :return: A tuple containing the parsed JSON response as a dictionary and the
            raw `requests.Response` object.
        :rtype: tuple[dict, requests.Response]
        """
        if data is None:
            data = {}
        return self._request_url("PUT", endpoint, data, e_tag)

    def _post_url(
            self,
            endpoint: str,
            e_tag: str |  None = None,
            data: dict | None = None
    ) -> tuple[dict, requests.Response]:
        """
        Sends a POST request to the specified endpoint with the given data and
        E-Tag header. This method forms a part of an internal HTTP interaction
        utility and is not intended for direct external use.

        :param endpoint: The URL endpoint to which the POST request should be sent.
        :type endpoint: str
        :param e_tag: The E-Tag header used for conditional request handling.
        :type e_tag: str
        :param data: Dictionary containing the JSON payload to be sent in the POST
                     request. Defaults to an empty dictionary if none is provided.
        :type data: dict | None
        :return: A tuple containing the JSON-decoded response content as a dictionary
                 and the raw `requests.Response` object from the POST request.
        :rtype: tuple[dict, requests.Response]
        """
        if data is None:
            data = {}
        return self._request_url("POST", endpoint, data, e_tag)

    def activate(
            self,
            sites: List = None,
            force: bool = False
    ) -> dict | None:
        """
        Activates pending changes for specific or all sites based on the input.

        This method is designed to activate configuration changes on the
        specified sites. If no sites are provided, it defaults to activating
        changes on all sites. It also provides the ability to force applying
        foreign changes if specified.

        :param sites: A list of site identifiers to be used to determine where the
                      configuration should be activated. If not provided or an
                      empty list, defaults to all sites.
        :type sites: List
        :param force: A boolean indicating whether to force applying foreign
                      changes.
        :type force: bool
        :return: Dictionary containing response data if the activation
                 succeeds, otherwise `None`.
        :rtype: dict | None
        """
        if sites is None:
            sites = []
        e_tag = self.get_activation_etag()
        postdata = {"redirect": False, "sites": sites, "force_foreign_changes": force}
        data, resp = self._post_url(
            endpoint="domain-types/activation_run/actions/activate-changes/invoke",
            e_tag=e_tag,
            data=postdata,
        )
        if resp.status_code == 200:
            return data
        else:
            resp.raise_for_status()
        return None

    def get_all_hosts(
            self,
            effective_attr: bool = False,
    ) -> Dict[Host, Any]:
        """
        Retrieve all host configurations with their respective extensions.

        This function communicates with a specified endpoint to fetch all host
        configurations. Each host configuration is encapsulated in a dictionary
        where its extensions are mapped to its unique identifier. Optionally,
        it can fetch effective attributes based on the user's input.

        :param effective_attr: A boolean flag indicating whether to retrieve
            effective attributes for each host configuration (True) or not
            (False). Defaults to False.
        :return: A dictionary where the keys are unique host IDs and the values
            are details about their extensions.
        :rtype: Dict[Host, Any]
        :raises HTTPError: If the endpoint response status code is not 200.
        """
        data, resp = self._get_url(
            endpoint=f"domain-types/host_config/collections/all",
            data={"effective_attributes": "true" if effective_attr else "false"},
        )
        if resp.status_code != 200:
            resp.raise_for_status()
        hosts = {}
        for host_info_dict in data.get("value", []):
            try:
                host_id = host_info_dict["id"]
                hosts[host_id] = host_info_dict["extensions"]
            except KeyError:
                pass
        return hosts

    def get_host(
            self,
            hostname: str
    ) -> dict | None:
        """
        Fetches the configuration of a host by its hostname.

        This method retrieves the host configuration data for a given hostname by
        making a request to the appropriate endpoint. If the request is successful,
        it returns the configuration data as a dictionary. Otherwise, it raises
        an exception if the response status code is not 200.

        :param hostname: The hostname of the host whose configuration is to be retrieved.
        :type hostname: str
        :return: A dictionary containing the host configuration data if the response
                 is successful, otherwise None.
        :rtype: dict | None
        :raises HTTPError: If the response status code is not 200.
        """
        data, resp = self._get_url(
            f"objects/host_config/{hostname}", data={"effective_attributes": "false"}
        )
        if resp.status_code == 200:
            return data
        resp.raise_for_status()
        return None

    def get_activation_etag(
            self
    ) -> str | None:
        """
        Retrieves the ETag header value for the pending changes of the activation run.

        This method fetches data from a URL specific to activation run pending changes and
        attempts to extract the ETag value from the response headers if the HTTP status code
        is 200. If the status code is not 200, it raises an exception based on the HTTP
        response.

        :raises HTTPError: If the HTTP response status is not 200.
        :return: The ETag value from the response headers if the request is successful,
                 or `None` if not present.
        :rtype: str | None
        """
        data, resp = self._get_url(
            f"/domain-types/activation_run/collections/pending_changes", data={}
        )
        if resp.status_code == 200:
            return resp.headers["etag"]
        resp.raise_for_status()
        return None

    def get_host_etag(
            self,
            hostname: Host
    ) -> str:
        """
        Retrieve the ETag (entity tag) of the specified host configuration. The function
        sends a GET request to fetch the configuration of the given host and, if successful,
        extracts the ETag value from the response headers. If the operation fails, an
        exception is raised with the details of the failed response.

        :param hostname: The host for which the ETag has to be retrieved.
        :type hostname: Host
        :return: The ETag value of the specified host.
        :rtype: str
        :raises RuntimeError: If the request fails or the response code is not 200.
        """
        data, resp = self._get_url(
            f"objects/host_config/{hostname}", data={"effective_attributes": "false"}
        )
        if resp.status_code == 200:
            logger.debug(f"Get etag for Host \"{hostname}\" successfully")
            return resp.headers.get('ETag', "")
        else:
            logger.critical(f"get etag for Host \"{hostname}\" with status code {resp.status_code} failed")
            logger.debug(f"request returns:\n{pformat(resp.json(), indent=4)}")
            raise RuntimeError(pformat(resp.json()))

    def get_version(
            self,
    ) -> dict | None:
        """
        Retrieves the version information by making a request to the appropriate endpoint.

        This method sends a request to the "version" URL to fetch version details. If the
        request is successful and returns a status code of 200, it returns the parsed data.
        If the request fails, an exception corresponding to the HTTP status is raised.

        :return: A dictionary containing version information if the request succeeds,
            or None if the request fails.
        :rtype: dict | None
        :raises HTTPError: If the response status code is not 200 and a failure occurs.
        """
        data, resp = self._get_url("version")
        if resp.status_code == 200:
            return data
        resp.raise_for_status()
        return None

    def get_labels(
            self,
            hostname: Host,
            object_type: str = "host"
    ) -> Labels:
        """
        Get currently defined labels of a host or service object from checkmk.

        This function retrieves the labels associated with a specific host or, optionally,
        a service object. Labels provide metadata or tags that can be used to identify or
        categorize hosts or services.

        :param hostname: Host object representing the target for label retrieval.
        :param object_type: Type of object being queried. Defaults to "host". Currently,
                            supports only "host". Type: str.
        :return: Labels of the respective object. May return an empty dictionary if no
                 labels are defined or if the specified object_type is unsupported.
        :rtype: Labels
        """
        labels: Labels = {}
        if object_type == "host":
            host = self.get_host(hostname)
            labels = host["extensions"]["attributes"].get("labels", {})
        elif object_type == "service":
            # maybe implemented in the future
            pass
        return labels

    def edit_host_label(
            self,
            hostname: Host,
            labels: Labels | None = None,
    ) -> bool:
        """
        Updates or removes labels associated with a specified host.

        This method allows you to update the labels of a given host or remove all
        associated labels when none are specified. The change is applied using
        the provided `hostname` and if applicable, the new `labels`.

        :param hostname: Host object representing the target host whose
            labels are to be updated or removed.
        :param labels: Labels object containing the new set of labels
            to assign to the host. If None, all labels will be removed.
        :return: A boolean value indicating whether the update or removal
            operation was successful.
        :rtype: bool
        """
        if labels:
            update_attributes = {"update_attributes": {"labels": labels}}
            logger.debug(f"update label(s) attributes for host \"{hostname}\" to {labels}")
        else:
            update_attributes = {"remove_attributes": ["labels"]}
            logger.debug(f"remove all host label(s) for host \"{hostname}\"")

        e_tag = self.get_host_etag(hostname)

        data, resp = self._put_url(
            endpoint=f"objects/host_config/{hostname}",
            e_tag=e_tag,
            data=update_attributes,
        )
        if resp.status_code == 200:
            logger.debug(f"Labels for Host \"{hostname}\" successfully updated")
            return True
        return False

    @staticmethod
    def remove_label(
            args: argparse.Namespace,
            host: Host,
            orig_labels: Labels,
            labels: Labels,
    ) -> Labels:
        """
        Removes specified labels from a given set of original labels and returns the updated label set.

        This method operates by iterating through the labels that need to be removed and comparing them to
        the original labels. If a match is found, the label is removed from the updated label set. If
        `testmode` is enabled in the arguments, the changes are logged as warnings without actual removal.

        :param args: An instance of `argparse.Namespace` containing optional `testmode` attribute.
        :type args: argparse.Namespace
        :param host: The host object from which the labels are being removed.
        :type host: Host
        :param orig_labels: Original set of labels before any modifications.
        :type orig_labels: Labels
        :param labels: The set of labels to be removed, specified as key-value pairs.
        :type labels: Labels
        :return: A new set of labels after removing the specified labels.
        :rtype: Labels
        """
        # working on a copy of the original labels
        updated_labels = orig_labels.copy()

        # remove all labels that should be removed
        for label, value in labels.items():
            for orig_label, orig_value in orig_labels.items():
                if orig_label.startswith(label) and (orig_value == value if value else True):
                    if args.testmode:
                        logger.warning(f"Testmode: Would remove label starting width \'{label}\' and value \'{value if value else "empty (ignored)"}\' from host: {host}")
                    else:
                        logger.warning(f"Remove label \'{label}\' and value \'{value if value else "empty (ignored)"}\' from host: {host}")
                    del updated_labels[label]
        return updated_labels

    @staticmethod
    def update_labels(
            orig_labels: Labels,
            new_labels: Labels,
            old_labels: Labels | None = None,
            cleanup: bool = False,
    ) -> Labels:
        """
        Updates the given `orig_labels` based on the `new_labels` and optionally the
        `old_labels` while adhering to the provided label cleanup strategies. The
        method performs cleanup or replacement operations based on the given
        labeling strategy and configuration.

        Parameters are as follows:

        :param orig_labels: Original set of labels to be updated.
        :param new_labels: New labels that will be applied or replace existing ones.
        :param old_labels: Optional. A set of old labels that will be removed.
        :param cleanup: Optional. A boolean flag indicating whether to force
            the application of cleanup strategies irrespective of label status.

        :return: The updated set of labels after applying cleanup and updates.
        :rtype: Labels
        """
        # {'hwsw/os_vendor': 'Ubuntu', 'hwsw/os_version': '20.04', 'test': 'xy'}
        # Cleanup: remove all labels with known prefix from original labels

        # working on a copy of the original labels
        updated_labels = orig_labels.copy()

        # find all labels that should be removed (labels that are created from labelpicker ald already existing)
        remove_keys = updated_labels.keys() & old_labels.keys()

        # remove all labels that should be removed
        for k in remove_keys:
            del updated_labels[k]

        # if not in cleanup mode, add new/ actual labels
        if not cleanup:
            updated_labels.update(new_labels)

        return updated_labels

    def get_inventory(self) -> dict:
        """
        Retrieve the inventory of hosts.

        Fetches the inventory data for all hosts from the specified endpoint and returns
        it as a dictionary where the keys are the host IDs and the values are the
        associated inventory details.

        :param self: Instance of the class.

        :returns:
            A dictionary mapping host IDs to their respective inventory details if the
            data is successfully fetched. Returns None if no data is available.

        :rtype: dict | None
        """
        data, resp = self._post_url(
            endpoint="/domain-types/host/collections/all",
            e_tag="*",
            data={
                "columns": ["name","mk_inventory"],
            },
        )
        resp.raise_for_status()
        inventories: Dict[str, Any] = {}
        for item in data.get("value", {}):
            inventories[item.get('id')] = item.get('extensions', {}).get('mk_inventory', {})
        return inventories
