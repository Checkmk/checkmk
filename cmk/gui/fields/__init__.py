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
    MetaData,
    NetworkScan,
    NetworkScanResult,
    SNMPCredentials,
)
from cmk.gui.fields.definitions import (
    attributes_field,
    column_field,
    customer_field,
    ExprSchema,
    FOLDER_PATTERN,
    FolderField,
    GroupField,
    HostField,
    Int,
    Integer,
    List,
    Nested,
    PasswordIdent,
    PasswordOwner,
    PasswordShare,
    PythonString,
    query_field,
    SiteField,
    Str,
    String,
    Timestamp,
    X509ReqPEMField,
)
from cmk.gui.fields.primitives import (
    Bool,
    Boolean,
    Constant,
    Date,
    DateTime,
    Decimal,
    Dict,
    Email,
    Function,
    IPv4,
    IPv4Interface,
    IPv6,
    IPv6Interface,
    Time,
    URL,
    UUID,
)
from cmk.gui.fields.validators import (
    ValidateAnyOfValidators,
    ValidateIPv4,
    ValidateIPv4Network,
    ValidateIPv6,
)

__all__ = [
    "attributes_field",
    "Bool",
    "Boolean",
    "column_field",
    "Constant",
    "customer_field",
    "Date",
    "DateTime",
    "Decimal",
    "Dict",
    "Email",
    "ExprSchema",
    "Field",
    "FolderField",
    "FOLDER_PATTERN",
    "Function",
    "GroupField",
    "HostAttributeManagementBoardField",
    "HostContactGroup",
    "HostField",
    "Int",
    "Integer",
    "IPMIParameters",
    "IPv4",
    "IPv4Interface",
    "IPv6",
    "IPv6Interface",
    "List",
    "MetaData",
    "missing_",
    "Nested",
    "NetworkScan",
    "NetworkScanResult",
    "PasswordIdent",
    "PasswordOwner",
    "PasswordShare",
    "query_field",
    "SiteField",
    "SNMPCredentials",
    "Str",
    "String",
    "Time",
    "Timestamp",
    "URL",
    "UUID",
    "ValidateAnyOfValidators",
    "ValidateIPv4",
    "ValidateIPv4Network",
    "ValidateIPv6",
    "X509ReqPEMField",
]
