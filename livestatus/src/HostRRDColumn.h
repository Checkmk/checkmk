// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostRRDColumn_h
#define HostRRDColumn_h

#include "config.h"  // IWYU pragma: keep

#include <optional>
#include <string>
#include <utility>

#include "RRDColumn.h"
#include "nagios.h"
class Row;

class HostRRDColumn : public RRDColumn {
public:
    using RRDColumn::RRDColumn;

private:
    [[nodiscard]] std::optional<std::pair<std::string, std::string>>
    getHostNameServiceDesc(Row row) const override {
        if (const auto *hst{columnData<host>(row)}) {
            return {{hst->name, dummy_service_description()}};
        }
        return {};
    }
};

#endif
