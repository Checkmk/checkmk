// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomVarsNamesColumn_h
#define CustomVarsNamesColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>
#include <vector>

#include "ListColumn.h"
#include "contact_fwd.h"
enum class AttributeKind;
class ColumnOffsets;
class MonitoringCore;
class Row;

class CustomVarsNamesColumn : public ListColumn {
public:
    CustomVarsNamesColumn(const std::string &name,
                          const std::string &description,
                          const ColumnOffsets &offsets,
                          const MonitoringCore *mc, AttributeKind kind)
        : ListColumn(name, description, offsets), _mc(mc), _kind(kind) {}

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    const MonitoringCore *const _mc;
    const AttributeKind _kind;
};

#endif  // CustomVarsNamesColumn_h
