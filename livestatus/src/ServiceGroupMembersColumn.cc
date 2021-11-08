// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceGroupMembersColumn.h"

#include "Logger.h"
#include "Renderer.h"

void ServiceGroupMembersRenderer::output(
    ListRenderer &l, const column::service_group_members::Entry &entry) const {
    switch (verbosity_) {
        case verbosity::none: {
            SublistRenderer s(l);
            s.output(entry.host_name);
            s.output(entry.description);
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(entry.host_name);
            s.output(entry.description);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<bool>(entry.has_been_checked));
            break;
        }
    }
}

namespace column::service_group_members::detail {
// value must be of the form
//    hostname hostservice_separator service_description
std::string checkValue(Logger *logger, RelationalOperator relOp,
                       const std::string &value) {
    auto pos = value.find(column::service_group_members::separator());
    bool equality = relOp == RelationalOperator::equal ||
                    relOp == RelationalOperator::not_equal;
    if (pos == std::string::npos && !(equality && value.empty())) {
        Informational(logger)
            << "Invalid reference value for service list membership. Must be 'hostname"
            << column::service_group_members::separator() << "servicename'";
    }
    return value;
}
}  // namespace column::service_group_members::detail
