// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CustomVarsExplicitColumn.h"
#include <unordered_map>
#include <utility>
#include "MonitoringCore.h"
#include "Row.h"

std::string CustomVarsExplicitColumn::getValue(Row row) const {
    if (auto p = columnData<void>(row)) {
        auto attrs = _mc->customAttributes(p, AttributeKind::custom_variables);
        auto it = attrs.find(_varname);
        if (it != attrs.end()) {
            return it->second;
        }
    }
    return "";
}
