// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceRRDColumn.h"
#include "Row.h"

class service;

[[nodiscard]] RRDColumn::Table ServiceRRDColumn::table() const {
    return RRDColumn::Table::services;
}

const void *ServiceRRDColumn::getObject(Row row) const {
    return columnData<service>(row);
}
