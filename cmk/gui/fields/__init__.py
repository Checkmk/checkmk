#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
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
from cmk.gui.fields.definitions import (
    attributes_field,
    column_field,
    customer_field,
    CustomFolderAttributes,
    CustomHostAttributes,
    ExprSchema,
    FOLDER_PATTERN,
    FolderField,
    GroupField,
    HostField,
    PasswordIdent,
    PasswordOwner,
    PasswordShare,
    PythonString,
    query_field,
    SiteField,
    Timestamp,
    X509ReqPEMFieldUUID,
)
from cmk.gui.fields.validators import ValidateHostName

__all__ = [
    "attributes_field",
    "column_field",
    "customer_field",
    "CustomFolderAttributes",
    "CustomHostAttributes",
    "ExprSchema",
    "Field",
    "FolderField",
    "FOLDER_PATTERN",
    "GroupField",
    "HostAttributeManagementBoardField",
    "HostContactGroup",
    "HostField",
    "IPMIParameters",
    "MetaData",
    "missing_",
    "NetworkScan",
    "NetworkScanResult",
    "LockedBy",
    "PasswordIdent",
    "PasswordOwner",
    "PasswordShare",
    "PythonString",
    "query_field",
    "SiteField",
    "SNMPCredentials",
    "Timestamp",
    "X509ReqPEMFieldUUID",
    "ValidateHostName",
]
