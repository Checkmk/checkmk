// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHost_h
#define NebHost_h

#include <memory>
#include <string>

#include "livestatus/Interface.h"
#include "nagios.h"

class NebHost : public IHost {
public:
    explicit NebHost(const ::host &host) : host_{host} {}
    [[nodiscard]] bool hasContact(const IContact &contact) const override;
    [[nodiscard]] const void *handle() const override { return &host_; }
    [[nodiscard]] std::string notificationPeriodName() const override;
    [[nodiscard]] std::string servicePeriodName() const override;

private:
    const ::host &host_;
};

std::unique_ptr<const IHost> ToIHost(const ::host *h);

#endif  // NebHost_h
