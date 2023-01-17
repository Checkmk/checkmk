// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContact_h
#define NebContact_h

#include <memory>

#include "livestatus/Interface.h"
#include "nagios.h"

class NebContact : public IContact {
public:
    explicit NebContact(const contact &contact) : contact_{contact} {}
    const void *handle() const override { return &contact_; };

private:
    const contact &contact_;
};

std::unique_ptr<const IContact> ToIContact(const contact *c);

#endif  // NebContact_h
