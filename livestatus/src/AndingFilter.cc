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
#include "OringFilter.h"
#include "logger.h"
#include "Query.h"

AndingFilter::~AndingFilter()
{
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        delete *it;
    }
}

void AndingFilter::addSubfilter(Filter *f)
{
    _subfilters.push_back(f);
}


Filter *AndingFilter::stealLastSubfiler()
{
    if (_subfilters.size() == 0)
        return 0;
    else {
        Filter *l = _subfilters.back();
        _subfilters.pop_back();
        return l;
    }
}


bool AndingFilter::accepts(void *data)
{
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        if (!filter->accepts(data))
            return false;
    }
    return true;
}

void *AndingFilter::findIndexFilter(const char *columnname)
{
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        void *refvalue = filter->indexFilter(columnname);
        if (refvalue)
            return refvalue;
    }
    return 0;
}

void AndingFilter::findIntLimits(const char *columnname, int *lower, int *upper)
{
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        filter->findIntLimits(columnname, lower, upper);
    }
}

bool AndingFilter::optimizeBitmask(const char *columnname, uint32_t *mask)
{
    bool optimized = false;
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        if (filter->optimizeBitmask(columnname, mask))
            optimized = true;
    }
    return optimized;
}

void AndingFilter::combineFilters(int count, int andor)
{
    if (count > (int)_subfilters.size()) {
        logger(LG_INFO, "Cannot combine %d filters with '%s': only %d are on stack",
                count, andor == ANDOR_AND ? "AND" : "OR", _subfilters.size());
        return;
    }

    AndingFilter *andorfilter; // OringFilter is subclassed from AndingFilter
    if (andor == ANDOR_AND)
        andorfilter = new AndingFilter();
    else
        andorfilter = new OringFilter();
    while (count--) {
        andorfilter->addSubfilter(_subfilters.back());
        _subfilters.pop_back();
    }
    addSubfilter(andorfilter);
}

