// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef auth_h
#define auth_h

#include "config.h"  // IWYU pragma: keep

#ifdef CMC
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif

enum class AuthorizationKind { loose = 0, strict = 1 };

#ifdef CMC
inline contact *unknown_auth_user() {
    return reinterpret_cast<contact *>(0xdeadbeaf);
}
#else
contact *unknown_auth_user();
class MonitoringCore;
bool is_authorized_for(MonitoringCore *mc, const contact *ctc, const host *hst,
                       const service *svc);
bool is_authorized_for_host_group(MonitoringCore *mc, const hostgroup *hg,
                                  const contact *ctc);
bool is_authorized_for_service_group(MonitoringCore *mc, const servicegroup *sg,
                                     const contact *ctc);
#endif

#endif  // auth_h
