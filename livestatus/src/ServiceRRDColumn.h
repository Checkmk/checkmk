// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceRRDColumn_h
#define ServiceRRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include "RRDColumn.h"

class Row;

class ServiceRRDColumn : public RRDColumn {
public:
    using RRDColumn::RRDColumn;

private:
    [[nodiscard]] Table table() const override;
    [[nodiscard]] const void *getObject(Row row) const override;
};

#endif
