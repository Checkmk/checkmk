#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Contacts(Table):
    __tablename__ = 'contacts'

    address1 = Column(
        'address1',
        col_type='string',
        description='The additional field address1',
    )
    """The additional field address1"""

    address2 = Column(
        'address2',
        col_type='string',
        description='The additional field address2',
    )
    """The additional field address2"""

    address3 = Column(
        'address3',
        col_type='string',
        description='The additional field address3',
    )
    """The additional field address3"""

    address4 = Column(
        'address4',
        col_type='string',
        description='The additional field address4',
    )
    """The additional field address4"""

    address5 = Column(
        'address5',
        col_type='string',
        description='The additional field address5',
    )
    """The additional field address5"""

    address6 = Column(
        'address6',
        col_type='string',
        description='The additional field address6',
    )
    """The additional field address6"""

    alias = Column(
        'alias',
        col_type='string',
        description='The full name of the contact',
    )
    """The full name of the contact"""

    can_submit_commands = Column(
        'can_submit_commands',
        col_type='int',
        description='Wether the contact is allowed to submit commands (0/1)',
    )
    """Wether the contact is allowed to submit commands (0/1)"""

    custom_variable_names = Column(
        'custom_variable_names',
        col_type='list',
        description='A list of the names of the custom variables',
    )
    """A list of the names of the custom variables"""

    custom_variable_values = Column(
        'custom_variable_values',
        col_type='list',
        description='A list of the values of the custom variables',
    )
    """A list of the values of the custom variables"""

    custom_variables = Column(
        'custom_variables',
        col_type='dict',
        description='A dictionary of the custom variables',
    )
    """A dictionary of the custom variables"""

    email = Column(
        'email',
        col_type='string',
        description='The email address of the contact',
    )
    """The email address of the contact"""

    host_notification_period = Column(
        'host_notification_period',
        col_type='string',
        description='The time period in which the contact will be notified about host problems',
    )
    """The time period in which the contact will be notified about host problems"""

    host_notifications_enabled = Column(
        'host_notifications_enabled',
        col_type='int',
        description='Wether the contact will be notified about host problems in general (0/1)',
    )
    """Wether the contact will be notified about host problems in general (0/1)"""

    in_host_notification_period = Column(
        'in_host_notification_period',
        col_type='int',
        description='Wether the contact is currently in his/her host notification period (0/1)',
    )
    """Wether the contact is currently in his/her host notification period (0/1)"""

    in_service_notification_period = Column(
        'in_service_notification_period',
        col_type='int',
        description='Wether the contact is currently in his/her service notification period (0/1)',
    )
    """Wether the contact is currently in his/her service notification period (0/1)"""

    label_names = Column(
        'label_names',
        col_type='list',
        description='A list of the names of the labels',
    )
    """A list of the names of the labels"""

    label_source_names = Column(
        'label_source_names',
        col_type='list',
        description='A list of the names of the label sources',
    )
    """A list of the names of the label sources"""

    label_source_values = Column(
        'label_source_values',
        col_type='list',
        description='A list of the values of the label sources',
    )
    """A list of the values of the label sources"""

    label_sources = Column(
        'label_sources',
        col_type='dict',
        description='A dictionary of the label sources',
    )
    """A dictionary of the label sources"""

    label_values = Column(
        'label_values',
        col_type='list',
        description='A list of the values of the labels',
    )
    """A list of the values of the labels"""

    labels = Column(
        'labels',
        col_type='dict',
        description='A dictionary of the labels',
    )
    """A dictionary of the labels"""

    modified_attributes = Column(
        'modified_attributes',
        col_type='int',
        description='A bitmask specifying which attributes have been modified',
    )
    """A bitmask specifying which attributes have been modified"""

    modified_attributes_list = Column(
        'modified_attributes_list',
        col_type='list',
        description='A list of all modified attributes',
    )
    """A list of all modified attributes"""

    name = Column(
        'name',
        col_type='string',
        description='The login name of the contact person',
    )
    """The login name of the contact person"""

    pager = Column(
        'pager',
        col_type='string',
        description='The pager address of the contact',
    )
    """The pager address of the contact"""

    service_notification_period = Column(
        'service_notification_period',
        col_type='string',
        description='The time period in which the contact will be notified about service problems',
    )
    """The time period in which the contact will be notified about service problems"""

    service_notifications_enabled = Column(
        'service_notifications_enabled',
        col_type='int',
        description='Wether the contact will be notified about service problems in general (0/1)',
    )
    """Wether the contact will be notified about service problems in general (0/1)"""

    tag_names = Column(
        'tag_names',
        col_type='list',
        description='A list of the names of the tags',
    )
    """A list of the names of the tags"""

    tag_values = Column(
        'tag_values',
        col_type='list',
        description='A list of the values of the tags',
    )
    """A list of the values of the tags"""

    tags = Column(
        'tags',
        col_type='dict',
        description='A dictionary of the tags',
    )
    """A dictionary of the tags"""
