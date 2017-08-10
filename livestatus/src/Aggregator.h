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

#ifndef Aggregator_h
#define Aggregator_h

#include "config.h"  // IWYU pragma: keep
#include "Renderer.h"
#include "Row.h"
class Query;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

enum class StatsOperation { count, sum, min, max, avg, std, suminv, avginv };

class Aggregator {
public:
    explicit Aggregator(StatsOperation operation) : _operation(operation) {}
    virtual ~Aggregator() = default;
    StatsOperation getOperation() const { return _operation; }

    // TODO(sp) Get rid of the contact* paramter once IntColumn::getValue is
    // fixed, it is just an artifact.
    virtual void consume(Row row, contact *auth_user, int timezone_offset) = 0;

    virtual void output(RowRenderer &r) const = 0;

private:
    const StatsOperation _operation;
};

#endif  // Aggregator_h
