// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebHost.h"

// Older Nagios headers are not const-correct... :-P
bool NebHost::hasContact(const IContact &contact) const {
    auto *h = const_cast<::host *>(&host_);
    auto *c = const_cast<::contact *>(
        static_cast<const ::contact *>(contact.handle()));
    return ::is_contact_for_host(h, c) != 0 ||
           ::is_escalated_contact_for_host(h, c) != 0;
}

std::unique_ptr<const IHost> ToIHost(const ::host *h) {
    return h != nullptr ? std::make_unique<NebHost>(*h) : nullptr;
}
