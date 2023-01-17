// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebService_h
#define NebService_h

#include <memory>

#include "NebHost.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebService : public IService {
public:
    explicit NebService(const ::service &svc)
        : host_{*svc.host_ptr}, service_{svc} {}
    [[nodiscard]] bool hasContact(const IContact &contact) const override;
    [[nodiscard]] const IHost &host() const override { return host_; }

private:
    const NebHost host_;
    const ::service &service_;
};

std::unique_ptr<const IService> ToIService(::service *s);

#endif  // NebService_h
