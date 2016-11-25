// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "VariadicFilter.h"
#include "AndingFilter.h"
#include "FilterVisitor.h"
#include "OringFilter.h"

using std::make_unique;
using std::string;
using std::unique_ptr;

// static
unique_ptr<VariadicFilter> VariadicFilter::make(LogicalOperator logicOp) {
    switch (logicOp) {
        case LogicalOperator::and_:
            return make_unique<AndingFilter>();
        case LogicalOperator::or_:
            return make_unique<OringFilter>();
    }
    return nullptr;  // unreachable
}

VariadicFilter::~VariadicFilter() {
    for (auto &subfilter : _subfilters) {
        delete subfilter;
    }
}

void VariadicFilter::accept(FilterVisitor &v) { v.visit(*this); }

void VariadicFilter::addSubfilter(Filter *f) { _subfilters.push_back(f); }

Filter *VariadicFilter::stealLastSubfiler() {
    if (_subfilters.empty()) {
        return nullptr;
    }
    Filter *l = _subfilters.back();
    _subfilters.pop_back();
    return l;
}

void VariadicFilter::findIntLimits(const string &colum_nname, int *lower,
                                   int *upper, int timezone_offset) const {
    for (auto filter : _subfilters) {
        filter->findIntLimits(colum_nname, lower, upper, timezone_offset);
    }
}

void VariadicFilter::combineFilters(int count, LogicalOperator andor) {
    auto variadic = VariadicFilter::make(andor);
    for (auto i = 0; i < count; ++i) {
        variadic->addSubfilter(_subfilters.back());
        _subfilters.pop_back();
    }
    // TODO(sp) Use unique_ptr in addSubfilter.
    addSubfilter(variadic.release());
}
