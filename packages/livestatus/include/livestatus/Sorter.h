// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Sorter_h
#define Sorter_h

class Row;

// StrongOrdering::notimplemented is a place holder to let us
// implement the ordering of the different column types one
// after the other.
// See also:
// https://en.cppreference.com/w/cpp/language/default_comparisons
enum StrongOrdering { equal, less, greater, notimplemented };

struct Sorter {
    Sorter() = default;
    virtual ~Sorter() = default;
    [[nodiscard]] virtual StrongOrdering compare(Row) const = 0;
};

#endif
