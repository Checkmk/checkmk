// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListStateColumn_h
#define HostListStateColumn_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <string>
#include "Column.h"
#include "IntColumn.h"
#include "ServiceListStateColumn.h"
class MonitoringCore;
class Row;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

class HostListStateColumn : public IntColumn {
public:
    // TODO(sp) Remove the magic arithmetic
    enum class Type {
        num_svc = static_cast<int>(ServiceListStateColumn::Type::num),
        num_svc_pending =
            static_cast<int>(ServiceListStateColumn::Type::num_pending),
        num_svc_ok = static_cast<int>(ServiceListStateColumn::Type::num_ok),
        num_svc_warn = static_cast<int>(ServiceListStateColumn::Type::num_warn),
        num_svc_crit = static_cast<int>(ServiceListStateColumn::Type::num_crit),
        num_svc_unknown =
            static_cast<int>(ServiceListStateColumn::Type::num_unknown),
        worst_svc_state =
            static_cast<int>(ServiceListStateColumn::Type::worst_state),
        num_svc_hard_ok =
            static_cast<int>(ServiceListStateColumn::Type::num_hard_ok),
        num_svc_hard_warn =
            static_cast<int>(ServiceListStateColumn::Type::num_hard_warn),
        num_svc_hard_crit =
            static_cast<int>(ServiceListStateColumn::Type::num_hard_crit),
        num_svc_hard_unknown =
            static_cast<int>(ServiceListStateColumn::Type::num_hard_unknown),
        worst_svc_hard_state =
            static_cast<int>(ServiceListStateColumn::Type::worst_hard_state),
        num_hst_up = 10,
        num_hst_down = 11,
        num_hst_unreach = 12,
        num_hst_pending = 13,
        num_hst = -11,
        worst_hst_state = -12,
    };

    HostListStateColumn(const std::string &name, const std::string &description,
                        Offsets offsets, MonitoringCore *mc, Type logictype)
        : IntColumn(name, description, offsets)
        , _mc(mc)
        , _logictype(logictype) {}

    int32_t getValue(Row row, const contact *auth_user) const override;

private:
    MonitoringCore *_mc;
    const Type _logictype;

    void update(host *hst, const contact *auth_user, int32_t &result) const;
};

#endif  // HostListStateColumn_h
