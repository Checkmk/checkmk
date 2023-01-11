// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHost_h
#define NebHost_h

#include <memory>

#include "livestatus/Interface.h"
struct host_struct;

class NebHost : public IHost {
public:
    explicit NebHost(const host_struct &host) : host_{host} {}
    bool hasContact(const IContact &contact) const override;

private:
    const host_struct &host_;
};

std::unique_ptr<const IHost> ToIHost(const host_struct *h);

#endif  // NebHost_h
