// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostRRDColumn.h"

#include <string>

#include "Metric.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "nagios.h"
#include "pnp4nagios.h"

RRDColumn::Data HostRRDColumn::getDataFor(Row row) const {
    if (const auto *hst{columnData<host>(row)}) {
        return getData(_mc->loggerRRD(), _mc->rrdcachedSocketPath(), _args,
                       [this, hst](const Metric::Name &var) {
                           return _mc->metricLocation(
                               hst->name, dummy_service_description(), var);
                       });
    }
    return {};
}
