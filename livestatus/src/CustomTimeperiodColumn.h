// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomTimeperiodColumn_h
#define CustomTimeperiodColumn_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <string>
#include <utility>
#include "Column.h"
#include "IntColumn.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class CustomTimeperiodColumn : public IntColumn {
public:
    CustomTimeperiodColumn(const std::string &name,
                           const std::string &description, Offsets offsets,
                           const MonitoringCore *mc, std::string varname)
        : IntColumn(name, description, offsets)
        , _mc(mc)
        , _varname(std::move(varname)) {}

    int32_t getValue(Row row, const contact *auth_user) const override;

private:
    const MonitoringCore *const _mc;
    std::string _varname;
};

#endif  // CustomTimeperiodColumn_h
