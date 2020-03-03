// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringPointerColumn_h
#define StringPointerColumn_h

#include "config.h"  // IWYU pragma: keep
#include "Column.h"
#include "StringColumn.h"

class StringPointerColumn : public StringColumn {
public:
    StringPointerColumn(const std::string &name, const std::string &description,
                        const Column::Offsets &offsets, const char *string)
        : StringColumn(name, description, offsets)
        //-1, -1, -1, 0)
        , _string(string) {}

    [[nodiscard]] std::string getValue(Row /*unused*/) const override {
        return _string;
    }

private:
    const char *const _string;
};

#endif  // StringPointerColumn_h
