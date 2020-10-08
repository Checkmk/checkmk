// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DynamicColumn.h"

#include <utility>

#include "Column.h"
#include "Logger.h"

DynamicColumn::DynamicColumn(std::string name, std::string description,
                             ColumnOffsets offsets)
    : _name(std::move(name))
    , _description(std::move(description))
    , _offsets(std::move(offsets)) {}

DynamicColumn::~DynamicColumn() = default;

std::string DynamicColumn::name() const { return _name; }
