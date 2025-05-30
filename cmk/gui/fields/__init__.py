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


from marshmallow.fields import (  # type: ignore[attr-defined,unused-ignore]
    Field,
    missing_,
)

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
    CertPrivateKey,
    CertPublicKey,
    ContactGroupField,
    GlobalHTTPProxyField,
    IPField,
    LDAPConnectionID,
    NetworkPortNumber,
    PasswordStoreIDField,
    RelativeUrl,
    SAMLConnectionID,
    ServiceLevelField,
    SplunkURLField,
    TagGroupIDField,
    Timeout,
    TimePeriodIDField,
    UnixPath,
)
from cmk.gui.fields.definitions import (
    bake_agent_field,
    column_field,
    customer_field,
    ExprSchema,
    FOLDER_PATTERN,
    FolderField,
    FolderIDField,
    GroupField,
    HostField,
    HostnameOrIP,
    PasswordEditableBy,
    PasswordIdent,
    PasswordShare,
    PythonString,
    query_field,
    SiteField,
    Timestamp,
    Username,
    UserRoleID,
    X509ReqPEMFieldUUID,
)

__all__ = [
    "AuxTagIDField",
    "bake_agent_field",
    "CertPublicKey",
    "CertPrivateKey",
    "column_field",
    "ContactGroupField",
    "customer_field",
    "ExprSchema",
    "Field",
    "FolderField",
    "FolderIDField",
    "FOLDER_PATTERN",
    "GlobalHTTPProxyField",
    "GroupField",
    "HostAttributeManagementBoardField",
    "HostContactGroup",
    "HostField",
    "HostnameOrIP",
    "TagGroupIDField",
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
    "PasswordEditableBy",
    "PasswordIdent",
    "PasswordShare",
    "PythonString",
    "query_field",
    "ServiceLevelField",
    "SiteField",
    "SplunkURLField",
    "SAMLConnectionID",
    "SNMPCredentials",
    "Timeout",
    "TimePeriodIDField",
    "Timestamp",
    "UnixPath",
    "Username",
    "UserRoleID",
    "RelativeUrl",
    "X509ReqPEMFieldUUID",
]
