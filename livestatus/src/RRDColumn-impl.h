// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_impl_h
#define RRDColumn_impl_h

#include "config.h"  // IWYU pragma: keep

#include <optional>
#include <string>
#include <utility>

#include "RRDColumn.h"

template <>
[[nodiscard]] inline std::optional<std::pair<std::string, std::string>>
RRDColumn<host_struct>::getHostNameServiceDesc(Row row) const {
    if (const auto *hst{columnData<host>(row)}) {
        return {{hst->name, dummy_service_description()}};
    }
    return {};
}

template <>
[[nodiscard]] inline std::optional<std::pair<std::string, std::string>>
RRDColumn<service_struct>::getHostNameServiceDesc(Row row) const {
    if (const auto *svc{columnData<service>(row)}) {
        return {{svc->host_name, svc->description}};
    }
    return {};
}

#endif
