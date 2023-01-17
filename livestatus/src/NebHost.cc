// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebHost.h"

#include <unordered_map>
#include <utility>

#include "NagiosCore.h"
#include "livestatus/Attributes.h"
#include "nagios.h"

// Older Nagios headers are not const-correct... :-P
bool NebHost::hasContact(const IContact &contact) const {
    auto *h = const_cast<::host *>(&host_);
    auto *c = const_cast<::contact *>(
        static_cast<const ::contact *>(contact.handle()));
    return ::is_contact_for_host(h, c) != 0 ||
           ::is_escalated_contact_for_host(h, c) != 0;
}

std::string NebHost::notificationPeriodName() const {
    const auto *np = host_.notification_period;
    return np == nullptr ? "" : np;
}

std::string NebHost::servicePeriodName() const {
    auto attrs = CustomAttributes(host_.custom_variables,
                                  AttributeKind::custom_variables);
    auto it = attrs.find("SERVICE_PERIOD");
    return it == attrs.end() ? "" : it->second;
}

std::unique_ptr<const IHost> ToIHost(const ::host *h) {
    return h != nullptr ? std::make_unique<NebHost>(*h) : nullptr;
}
