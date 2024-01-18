// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DictSorter_h
#define DictSorter_h

#include "Row.h"
#include "Sorter.h"

struct DictStrValueSorter : Sorter {
    [[nodiscard]] StrongOrdering compare(Row /*row*/) const override {
        return StrongOrdering::notimplemented;
    }
};

struct DictDoubleValueSorter : Sorter {
    [[nodiscard]] StrongOrdering compare(Row /*row*/) const override {
        return StrongOrdering::notimplemented;
    }
};

#endif
