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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "AndingFilter.h"
#include <cinttypes>
#include "OringFilter.h"
#include "Query.h"
#include "logger.h"

AndingFilter::~AndingFilter() {
    for (auto &subfilter : _subfilters) {
        delete subfilter;
    }
}

void AndingFilter::addSubfilter(Filter *f) { _subfilters.push_back(f); }

Filter *AndingFilter::stealLastSubfiler() {
    if (_subfilters.empty()) {
        return nullptr;
    }
    Filter *l = _subfilters.back();
    _subfilters.pop_back();
    return l;
}

bool AndingFilter::accepts(void *data) {
    for (auto filter : _subfilters) {
        if (!filter->accepts(data)) {
            return false;
        }
    }
    return true;
}

void *AndingFilter::findIndexFilter(const char *columnname) {
    for (auto filter : _subfilters) {
        void *refvalue = filter->indexFilter(columnname);
        if (refvalue != nullptr) {
            return refvalue;
        }
    }
    return nullptr;
}

void AndingFilter::findIntLimits(const char *columnname, int *lower,
                                 int *upper) {
    for (auto filter : _subfilters) {
        filter->findIntLimits(columnname, lower, upper);
    }
}

bool AndingFilter::optimizeBitmask(const char *columnname, uint32_t *mask) {
    bool optimized = false;
    for (auto filter : _subfilters) {
        if (filter->optimizeBitmask(columnname, mask)) {
            optimized = true;
        }
    }
    return optimized;
}

void AndingFilter::combineFilters(int count, int andor) {
    if (count > static_cast<int>(_subfilters.size())) {
        logger(LG_INFO, "Cannot combine %d filters with '%s': only %" PRIuMAX
                        " are on stack",
               count, andor == ANDOR_AND ? "AND" : "OR",
               static_cast<uintmax_t>(_subfilters.size()));
        return;
    }

    AndingFilter *andorfilter;  // OringFilter is subclassed from AndingFilter
    if (andor == ANDOR_AND) {
        andorfilter = new AndingFilter();
    } else {
        andorfilter = new OringFilter();
    }
    while ((count--) != 0) {
        andorfilter->addSubfilter(_subfilters.back());
        _subfilters.pop_back();
    }
    addSubfilter(andorfilter);
}
