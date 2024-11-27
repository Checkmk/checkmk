// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebDowntime_h
#define NebDowntime_h

#include "livestatus/Interface.h"
#include "neb/Downtime.h"
#include "neb/NebHost.h"
#include "neb/NebService.h"

class NebDowntime : public IDowntime {
public:
    NebDowntime(const Downtime &downtime, const IHost &host,
                const IService *service)
        : downtime_{downtime}, host_{host}, service_{service} {}

    [[nodiscard]] int32_t id() const override { return downtime_._id; }

    [[nodiscard]] std::string author() const override {
        return downtime_._author;
    }

    [[nodiscard]] std::string comment() const override {
        return downtime_._comment;
    }

    [[nodiscard]] bool origin_is_rule() const override { return false; }

    [[nodiscard]] std::chrono::system_clock::time_point entry_time()
        const override {
        return downtime_._entry_time;
    }

    [[nodiscard]] std::chrono::system_clock::time_point start_time()
        const override {
        return downtime_._start_time;
    }

    [[nodiscard]] std::chrono::system_clock::time_point end_time()
        const override {
        return downtime_._end_time;
    }

    [[nodiscard]] bool isService() const override {
        return downtime_._service != nullptr;
    }

    [[nodiscard]] bool fixed() const override { return downtime_._fixed; }

    [[nodiscard]] std::chrono::nanoseconds duration() const override {
        return downtime_._duration;
    }

    [[nodiscard]] RecurringKind recurring() const override {
        return RecurringKind::none;
    }

    [[nodiscard]] bool pending() const override {
        return !downtime_._is_active;
    }

    [[nodiscard]] int32_t triggered_by() const override {
        return downtime_._triggered_by;
    };

    [[nodiscard]] const IHost &host() const override { return host_; }

    [[nodiscard]] const IService *service() const override { return service_; }

private:
    const Downtime &downtime_;
    const IHost &host_;
    const IService *service_;
};

#endif  // NebDowntime_h
