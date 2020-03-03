// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListStateColumn_h
#define ServiceListStateColumn_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <string>
#include "Column.h"
#include "IntColumn.h"
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
    // TODO(sp) Remove the magic arithmetic
    enum class Type {
        num_ok = 0,
        num_warn = 1,
        num_crit = 2,
        num_unknown = 3,
        num_pending = 4,
        worst_state = -2,
        num_hard_ok = (0 + 64),
        num_hard_warn = (1 + 64),
        num_hard_crit = (2 + 64),
        num_hard_unknown = (3 + 64),
        worst_hard_state = (-2 + 64),
        num = -1
    };

    ServiceListStateColumn(const std::string &name,
                           const std::string &description,
                           const Column::Offsets &offsets, MonitoringCore *mc,
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

    static void update(Type logictype, service *svc, int32_t &result);
};

#endif  // ServiceListStateColumn_h
