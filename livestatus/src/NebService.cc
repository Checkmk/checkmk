// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebService.h"

// Older Nagios headers are not const-correct... :-P
bool NebService::hasContact(const IContact &contact) const {
    auto *s = const_cast<::service *>(&service_);
    auto *c = const_cast<::contact *>(
        static_cast<const ::contact *>(contact.handle()));
    return is_contact_for_service(s, c) != 0 ||
           is_escalated_contact_for_service(s, c) != 0;
}

std::unique_ptr<const IService> ToIService(::service *s) {
    return s != nullptr ? std::make_unique<NebService>(*s) : nullptr;
}
