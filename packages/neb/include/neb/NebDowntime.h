// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebDowntime_h
#define NebDowntime_h

#include <chrono>
#include <cstdint>
#include <string>

#include "livestatus/Interface.h"

class Downtime;

class NebDowntime : public IDowntime {
public:
    NebDowntime(const Downtime &downtime, const IHost &host,
                const IService *service)
        : downtime_{downtime}, host_{host}, service_{service} {}

    [[nodiscard]] int32_t id() const override;
    [[nodiscard]] std::string author() const override;
    [[nodiscard]] std::string comment() const override;
    [[nodiscard]] bool origin_is_rule() const override;
    [[nodiscard]] std::chrono::system_clock::time_point entry_time()
        const override;
    [[nodiscard]] std::chrono::system_clock::time_point start_time()
        const override;
    [[nodiscard]] std::chrono::system_clock::time_point end_time()
        const override;
    [[nodiscard]] bool isService() const override;
    [[nodiscard]] bool fixed() const override;
    [[nodiscard]] std::chrono::nanoseconds duration() const override;
    [[nodiscard]] RecurringKind recurring() const override;
    [[nodiscard]] bool pending() const override;
    [[nodiscard]] int32_t triggered_by() const override;
    [[nodiscard]] const IHost &host() const override { return host_; }
    [[nodiscard]] const IService *service() const override { return service_; }

private:
    const Downtime &downtime_;
    const IHost &host_;
    const IService *service_;
};

#endif  // NebDowntime_h
