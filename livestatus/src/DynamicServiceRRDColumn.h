// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicServiceRRDColumn_h
#define DynamicServiceRRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "DynamicRRDColumn.h"

class Column;

class DynamicServiceRRDColumn : public DynamicRRDColumn {
public:
    using DynamicRRDColumn::DynamicRRDColumn;
    std::unique_ptr<Column> createColumn(const std::string &name,
                                         const std::string &arguments) override;
};

#endif
