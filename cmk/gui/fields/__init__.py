#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# import warnings
# from marshmallow.warnings import RemovedInMarshmallow4Warning
# NOTE
# This warning is not permanently an error, so that no new warnings will be introduced by
# unsuspecting developers.
# This could be moved to the test setup, so it won't make trouble for our users.
# warnings.simplefilter("error", RemovedInMarshmallow4Warning)


from marshmallow.fields import Field, missing_

from cmk.gui.fields.attributes import (
    HostAttributeManagementBoardField,
    HostContactGroup,
    IPMIParameters,
    LockedBy,
    MetaData,
    NetworkScan,
    NetworkScanResult,
    SNMPCredentials,
)
from cmk.gui.fields.custom_fields import (
    AuxTagIDField,
    ContactGroupField,
    FolderIDField,
    IPField,
    LDAPConnectionID,
    NetworkPortNumber,
    PasswordStoreIDField,
    RelativeUrl,
    SplunkURLField,
    Timeout,
    TimePeriodIDField,
    UnixPath,
)
from cmk.gui.fields.definitions import (
    column_field,
    customer_field,
    CustomHostAttributes,
    ExprSchema,
    FOLDER_PATTERN,
    FolderField,
    GroupField,
    host_attributes_field,
    HostField,
    HostnameOrIP,
    PasswordIdent,
    PasswordOwner,
    PasswordShare,
    PythonString,
    query_field,
    SiteField,
    Timestamp,
    Username,
    X509ReqPEMFieldUUID,
)

__all__ = [
    "AuxTagIDField",
    "host_attributes_field",
    "column_field",
    "ContactGroupField",
    "customer_field",
    "CustomHostAttributes",
    "ExprSchema",
    "Field",
    "FolderField",
    "FolderIDField",
    "FOLDER_PATTERN",
    "GroupField",
    "HostAttributeManagementBoardField",
    "HostContactGroup",
    "HostField",
    "HostnameOrIP",
    "IPField",
    "IPMIParameters",
    "MetaData",
    "missing_",
    "NetworkPortNumber",
    "NetworkScan",
    "NetworkScanResult",
    "PasswordStoreIDField",
    "LDAPConnectionID",
    "LockedBy",
    "PasswordIdent",
    "PasswordOwner",
    "PasswordShare",
    "PythonString",
    "query_field",
    "SiteField",
    "SplunkURLField",
    "SNMPCredentials",
    "Timeout",
    "TimePeriodIDField",
    "Timestamp",
    "UnixPath",
    "Username",
    "RelativeUrl",
    "X509ReqPEMFieldUUID",
]
