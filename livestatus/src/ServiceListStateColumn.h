// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListStateColumn_h
#define ServiceListStateColumn_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <string>

#include "IntColumn.h"
#include "LogEntry.h"
class ColumnOffsets;
class MonitoringCore;
class Row;

#ifdef CMC
#include "Host.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

class ServiceListStateColumn : public IntColumn {
public:
    enum class Type {
        num,
        num_pending,
        num_handled_problems,
        num_unhandled_problems,
        //
        num_ok,
        num_warn,
        num_crit,
        num_unknown,
        worst_state,
        //
        num_hard_ok,
        num_hard_warn,
        num_hard_crit,
        num_hard_unknown,
        worst_hard_state,
    };

    ServiceListStateColumn(const std::string &name,
                           const std::string &description,
                           const ColumnOffsets &offsets, MonitoringCore *mc,
                           Type logictype)
        : IntColumn(name, description, offsets)
        , _mc(mc)
        , _logictype(logictype) {}

    int32_t getValue(Row row, const contact *auth_user) const override;

#ifdef CMC
    using service_list = const Host::services_t *;
#else
    using service_list = servicesmember *;
#endif

    static int32_t getValueFromServices(MonitoringCore *mc, Type logictype,
                                        service_list mem,
                                        const contact *auth_user);

private:
    MonitoringCore *_mc;
    const Type _logictype;

    static void update(Type logictype, ServiceState current_state,
                       ServiceState last_hard_state, bool has_been_checked,
                       bool handled, int32_t &result);
};

#endif  // ServiceListStateColumn_h
