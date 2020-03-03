// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BoolPointerColumn_h
#define BoolPointerColumn_h

#include "config.h"  // IWYU pragma: keep
#include "IntColumn.h"

class BoolPointerColumn : public IntColumn {
public:
    BoolPointerColumn(const std::string& name, const std::string& description,
                      const bool* pointer)
        : IntColumn(name, description, {}), _pointer(pointer) {}

    int32_t getValue(Row /* row */,
                     const contact* /* auth_user */) const override {
        return *_pointer ? 1 : 0;
    }

private:
    const bool* const _pointer;
};

#endif  // BoolPointerColumn_h
