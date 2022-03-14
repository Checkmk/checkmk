// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef pnp4nagios_h
#define pnp4nagios_h

#include "config.h"  // IWYU pragma: keep

#include <string>
#ifndef CMC
class MonitoringCore;
#endif

inline std::string dummy_service_description() { return "_HOST_"; }

std::string pnp_cleanup(const std::string &name);

#ifndef CMC
int pnpgraph_present(MonitoringCore *mc, const std::string &host,
                     const std::string &service);
#endif

#endif  // pnp4nagios_h
