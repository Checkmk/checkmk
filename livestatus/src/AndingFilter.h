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

#ifndef AndingFilter_h
#define AndingFilter_h

#include "config.h"

#include "Filter.h"
#include <deque>

class AndingFilter : public Filter
{
public:
    typedef deque<Filter *> _subfilters_t;

protected:
    _subfilters_t _subfilters;

public:
    AndingFilter() {}
    ~AndingFilter();
    bool isAndingFilter() { return true; }
    void addSubfilter(Filter *);
    Filter *stealLastSubfiler();
    bool accepts(void *data);
    void combineFilters(int count, int andor);
    unsigned numFilters() { return _subfilters.size(); }
    _subfilters_t::iterator begin() { return _subfilters.begin(); }
    _subfilters_t::iterator end() { return _subfilters.end(); }
    void *findIndexFilter(const char *columnname);
    void findIntLimits(const char *columnname, int *lower, int *upper);
    bool optimizeBitmask(const char *columnname, uint32_t *mask);
};


#endif // AndingFilter_h

