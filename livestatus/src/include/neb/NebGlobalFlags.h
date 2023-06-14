// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebGlobalFlags_h
#define NebGlobalFlags_h

#include "livestatus/Interface.h"
#include "neb/nagios.h"

class NebGlobalFlags : public IGlobalFlags {
public:
    [[nodiscard]] bool enable_notifications() const override {
        return ::enable_notifications != 0;
    }

    [[nodiscard]] bool execute_service_checks() const override {
        return ::execute_service_checks != 0;
    }

    [[nodiscard]] bool accept_passive_service_checks() const override {
        return ::accept_passive_service_checks != 0;
    }

    [[nodiscard]] bool execute_host_checks() const override {
        return ::execute_host_checks != 0;
    }

    [[nodiscard]] bool accept_passive_hostchecks() const override {
        return ::accept_passive_host_checks != 0;
    }

    [[nodiscard]] bool obsess_over_services() const override {
        return ::obsess_over_services != 0;
    }

    [[nodiscard]] bool obsess_over_hosts() const override {
        return ::obsess_over_hosts != 0;
    }

    [[nodiscard]] bool check_service_freshness() const override {
        return ::check_service_freshness != 0;
    }

    [[nodiscard]] bool check_host_freshness() const override {
        return ::check_host_freshness != 0;
    }

    [[nodiscard]] bool enable_flap_detection() const override {
        return ::enable_flap_detection != 0;
    }

    [[nodiscard]] bool process_performance_data() const override {
        return ::process_performance_data != 0;
    }

    [[nodiscard]] bool enable_event_handlers() const override {
        return ::enable_event_handlers != 0;
    }

    [[nodiscard]] bool check_external_commands() const override {
        return ::check_external_commands != 0;
    }
};

#endif  // NebGlobalFlags_h
