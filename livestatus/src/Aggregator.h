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
#include <cmath>
#include "Renderer.h"
#include "Row.h"
#include "contact_fwd.h"
class Query;

class Aggregation {
public:
    enum class operation { sum, min, max, avg, std, suminv, avginv };

    explicit Aggregation(operation op)
        : _operation(op), _count(0), _aggr(0), _sumq(0) {}

    void update(double value) {
        _count++;
        switch (_operation) {
            case Aggregation::operation::sum:
                _aggr += value;
                break;
            case Aggregation::operation::min:
                if (_count == 1 || value < _aggr) {
                    _aggr = value;
                }
                break;
            case Aggregation::operation::max:
                if (_count == 1 || value > _aggr) {
                    _aggr = value;
                }
                break;
            case Aggregation::operation::avg:
                _aggr += value;
                break;
            case Aggregation::operation::std:
                _aggr += value;
                _sumq += value * value;
                break;
            case Aggregation::operation::suminv:
                _aggr += 1.0 / value;
                break;
            case Aggregation::operation::avginv:
                _aggr += 1.0 / value;
                break;
        }
    }

    double value() const {
        switch (_operation) {
            case Aggregation::operation::sum:
                return _aggr;
            case Aggregation::operation::min:
                return _aggr;
            case Aggregation::operation::max:
                return _aggr;
            case Aggregation::operation::avg:
                return _aggr / _count;
            case Aggregation::operation::std: {
                auto mean = _aggr / _count;
                return sqrt(_sumq / _count - mean * mean);
            }
            case Aggregation::operation::suminv:
                return _aggr;
            case Aggregation::operation::avginv:
                return _aggr / _count;
        }
        return 0;  // unreachable
    }

private:
    operation _operation;
    std::uint32_t _count;
    double _aggr;
    double _sumq;
};

class Aggregator {
public:
    virtual ~Aggregator() = default;
    virtual void consume(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) = 0;
    virtual void output(RowRenderer &r) const = 0;
};

#endif  // Aggregator_h
