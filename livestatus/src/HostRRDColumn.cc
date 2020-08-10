// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostRRDColumn.h"

#include <filesystem>
#include <string>

#include "Metric.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "nagios.h"
#include "pnp4nagios.h"

RRDColumn::Data HostRRDColumn::getDataFor(Row row) const {
    if (const auto *hst{columnData<host>(row)}) {
        return getData(
            _mc->loggerRRD(), _mc->rrdcachedSocketPath(), _args,
            [this, hst](const Metric::Name &var) {
                return MetricLocation{
                    this->_mc->pnpPath() / hst->name /
                        pnp_cleanup(dummy_service_description() + "_" +
                                    Metric::MangledName(var).string() + ".rrd"),
                    "1"};
            });
    }
    return {};
}
