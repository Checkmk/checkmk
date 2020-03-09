// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceMetricsColumn_h
#define ServiceMetricsColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>
#include <vector>
#include "Column.h"
#include "MetricsColumn.h"
#include "contact_fwd.h"

class Row;
class MonitoringCore;

class ServiceMetricsColumn : public MetricsColumn {
public:
    ServiceMetricsColumn(const std::string& name,
                         const std::string& description,
                         const Column::Offsets& offsets, MonitoringCore* mc);

    std::vector<std::string> getValue(
        Row, const contact* /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override;

private:
    MonitoringCore* const _mc;
};

#endif
