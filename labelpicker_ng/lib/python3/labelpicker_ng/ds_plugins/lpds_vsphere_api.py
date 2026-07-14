#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2025 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
from typing import Literal
from pprint import pformat
from pydantic.json_schema import JsonValue
import requests, urllib3, json
from pydantic import BaseModel
from labelpicker_ng import logger


class VsphereApiConfig(BaseModel):
    """
    Verbindungsparameter für die VMware vCenter REST API.

    :ivar api_url: Basis-URL der vCenter API (z. B. "https://vcenter.example.org/api").
    :type api_url: str
    :ivar api_user: Benutzername für die API-Authentifizierung.
    :type api_user: str
    :ivar api_pass: Passwort bzw. API-Secret für den Benutzer.
    :type api_pass: str
    :ivar verify_ssl: SSL-Zertifikatsprüfung aktivieren. Akzeptiert bool/"truthy" Werte; Standard: True.
    :type verify_ssl: bool
    """
    api_url: str
    api_user: str
    api_pass: str
    verify_ssl: bool = True


class VsphereConfig(BaseModel):
    """
    Represents the configuration for connecting to vSphere.

    This class is used to store and manage the vSphere API configuration
    and additional properties useful for forming specific connection
    details like host suffix.

    :ivar api_config: Configuration object for vSphere API that holds
        necessary connection details.
    :type api_config: VsphereApiConfig
    :ivar host_suffix: Optional string suffix to append to host names
        when forming vSphere connections.
    :type host_suffix: str
    """
    api_config: VsphereApiConfig
    host_suffix: str = ""


class vSphereAPI:
    """
    Manages communication with VMware vCenter APIs for various operational tasks.

    This class is used to interact with the VMware vCenter API. It provides methods
    for authenticating with the API, fetching virtual machine data, retrieving tagging
    information, and performing various HTTP request operations.

    :ivar vsphere_config: Configuration details for vCenter API access, including
        the API URL, username, password, and SSL verification flag.
    :type vsphere_config: VsphereConfig
    :ivar sid: Authentication session ID used to authenticate requests with the API.
    :type sid: str
    """
    vsphere_config: VsphereApiConfig
    sid: str

    def __init__(
            self,
            vsphere_config: VsphereApiConfig
    ):
        """
        Initializes the class with the provided vSphere API configuration and handles
        the suppression of SSL warnings if the verification is disabled.

        :param vsphere_config: Configuration object containing vSphere API settings.
        :type vsphere_config: VsphereApiConfig
        """
        self.vsphere_config = vsphere_config
        # Disable SSL warnings if verify = false
        if not self.vsphere_config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.sid = self.auth_vcenter()

    def auth_vcenter(
            self
    ) -> str | None:
        """
        Authenticate with the VMware vCenter API to establish a session.

        This function sends a POST request to the VMware vCenter API session endpoint
        to authenticate using the provided username, password, and SSL verification flag.
        If the authentication fails, an error is logged, and the function returns None.

        :param self: The instance of the class calling this method.
        :return: The session token as a string if authentication is successful, or None
                 if authentication fails.
        :rtype: Optional[str]
        """
        url = "{}/com/vmware/cis/session".format(self.vsphere_config.api_url)
        resp = requests.post(
            url=url,
            auth=(self.vsphere_config.api_user, self.vsphere_config.api_pass),
            verify=self.vsphere_config.verify_ssl
        )
        if resp.status_code != 200:
            logger.error(f"API authentication failed with status code {resp.status_code}:\n"
                         f"{pformat(resp.text, indent=4)}")
            return None
        return resp.json().get("value")

    def make_request(
            self,
            method:  Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            url: str,
            headers=dict[str, str],
            data: JsonValue=None
    ):
        """
        Makes an HTTP request to the given URL using the specified method, headers, and data.
        The method is responsible for handling the HTTP request and provides error logging for
        unsuccessful responses. If the request is successful (status code 200), the response
        object is returned. Otherwise, `None` is returned.

        :param method: The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
        :type method: str
        :param url: The URL to which the HTTP request is sent.
        :type url: str
        :param headers: Optional HTTP headers to include in the request.
        :type headers: dict, optional
        :param data: Optional data to send with the HTTP request.
        :type data: dict, str, bytes, or None, optional
        :return: The response object if the request is successful, otherwise `None`.
        :rtype: requests.Response or None
        """
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            verify=self.vsphere_config.verify_ssl
        )
        if resp.status_code != 200:
            logger.error(f"API request failed with status code {resp.status_code}:\n"
                         f"{pformat(resp.text, indent=4)}")
            return None
        return resp

    def get_api_data(
            self,
            req_url: str,
    ) -> JsonValue:
        """
        Fetches data from a specified API endpoint using the provided request URL.

        This method sends a GET request to the given URL with the session ID
        included in the request headers. It returns the parsed JSON response
        data if the request is successful. If no response is obtained, it
        returns None.

        :param req_url: The API endpoint URL to fetch the data from.
        :type req_url: str

        :return: The parsed JSON response if the request is successful;
            otherwise, None.
        :rtype: dict or None
        """
        headers = {"vmware-api-session-id": self.sid}
        resp = self.make_request(
            method="GET",
            url=req_url,
            headers=headers
        )
        return resp.json() if resp else None

    def post_api_data(
            self,
            req_url: str,
            req_data: JsonValue,
    ) -> JsonValue | None:
        """
        Sends a POST request to the specified API URL with the provided data. The method
        formats the request by including required headers and ensures the data is
        properly serialized as JSON before sending it.

        :param req_url: The URL to which the POST request will be sent.
        :type req_url: str
        :param req_data: The dictionary containing the data payload to be sent in the
            POST request.
        :type req_data: dict
        :return: The JSON-decoded response content if the request is successful,
            or None if the response is invalid.
        :rtype: dict or None
        """
        headers = {
            "vmware-api-session-id": self.sid,
            "content-type": "application/json",
        }
        data = json.dumps(req_data)
        resp = self.make_request(
            method="POST",
            url=req_url,
            headers=headers,
            data=data
        )
        return resp.json() if resp else None

    def get_all_vms(
            self
    ) -> list[dict] | None:
        """
        Fetches and returns all virtual machines from the vCenter API.

        This method retrieves data from the vCenter API endpoint for virtual machines.
        If successful, it extracts and returns the relevant values from the API
        response. If the response is empty or invalid, it returns None.

        :return: A list of all virtual machines retrieved from the API, or None if
            the response is empty or invalid
        :rtype: list or None
        """
        resp = self.get_api_data(f"{self.vsphere_config.api_url}/vcenter/vm")
        return resp.get("value") if resp else None

    def get_vm_tags(
            self,
            vm_id: str,
    ) -> list[dict] | None:
        """
        Fetches a list of tags attached to a specific virtual machine (VM) by its ID.

        This method sends a POST request to the API endpoint to retrieve the tags
        associated with the given VM. The request includes the VM ID and its object type.
        If any tags are found, they are returned; otherwise, the response is None.

        :param vm_id: The unique identifier of the virtual machine for which the tags
            are to be retrieved.
        :type vm_id: str
        :return: A list of tags attached to the specified VM if available, otherwise None.
        :rtype: list or None
        """
        url = "{}/com/vmware/cis/tagging/tag-association?~action=list-attached-tags".format(
            self.vsphere_config.api_url
        )
        req_data = {"object_id": {"type": "VirtualMachine", "id": vm_id}}
        resp = self.post_api_data(url, req_data)
        return resp.get('value', None)

    def get_tag_category(
            self,
            cat_id: str
    ) -> dict | None:
        """
        Fetches the tagging category details for the given category ID by making an API request.
        It constructs the appropriate URL with the category ID and retrieves the data
        using the `get_api_data` method.

        :param cat_id: The unique identifier of the tagging category to fetch.
        :type cat_id: str
        :return: The response data retrieved for the given category ID, or None if no data exists.
        :rtype: dict or None
        """
        url = "{}/com/vmware/cis/tagging/category/id:{}".format(self.vsphere_config.api_url, cat_id)
        resp = self.get_api_data(url)
        return resp if resp else None

    def get_vsphere_tag(
            self,
            tag_id: str
    ) -> dict | None:
        """
        Fetches the details of a vSphere tag using its unique identifier.

        This method constructs the API URL for retrieving the specified vSphere tag,
        makes a GET request to fetch the tag data, and returns the response.

        :param tag_id: Unique identifier of the vSphere tag used to fetch the tag details
        :type tag_id: str
        :return: The response data containing the vSphere tag details if found, otherwise None
        :rtype: dict or None
        """
        url = "{}/com/vmware/cis/tagging/tag/id:{}".format(self.vsphere_config.api_url, tag_id)
        resp = self.get_api_data(url)
        return resp if resp else None
