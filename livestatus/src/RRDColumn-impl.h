// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
#include "pnp4nagios.h"

template <>
[[nodiscard]] inline std::optional<std::pair<std::string, std::string>>
detail::RRDDataMaker::getHostNameServiceDesc(const host* row) {
    if (const auto* hst{row}) {
        return {{hst->name, dummy_service_description()}};
    }
    return {};
}

template <>
[[nodiscard]] inline std::optional<std::pair<std::string, std::string>>
detail::RRDDataMaker::getHostNameServiceDesc(const service* row) {
    if (const auto* svc{row}) {
        return {{svc->host_name, svc->description}};
    }
    return {};
}

#endif
