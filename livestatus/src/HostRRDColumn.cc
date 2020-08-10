// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostRRDColumn.h"

#include "Logger.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "nagios.h"

RRDColumn::Data HostRRDColumn::getDataFor(Row row) const {
    ObjectPointer object{columnData<host>(row),
                         RRDColumn::ObjectPointer::Kind::hosts};
    if (object.ptr == nullptr) {
        Warning(_mc->loggerRRD()) << "Missing object pointer for RRDColumn";
        return {};
    }
    return getData(_mc->loggerRRD(), _mc->rrdcachedSocketPath(), _args,
                   [this, object](const Metric::Name &var) {
                       return this->_mc->metricLocation(
                           object, Metric::MangledName(var));
                   });
}
