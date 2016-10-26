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

#ifndef Column_h
#define Column_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "opids.h"
class Filter;
class Logger;
class RowRenderer;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

enum class ColumnType { int_, double_, string, list, time, dict, blob, null };

class Column {
public:
    Column(std::string name, std::string description, int indirect_offset,
           int extra_offset, int extra_extra_offset = -1);
    virtual ~Column() {}

    std::string name() const { return _name; }
    std::string description() const { return _description; }
    void *shiftPointer(void *data) const;

    // TODO(sp) Get rid of the contact* paramter once IntColumn::getValue is
    // fixed, it is just an artifact.
    virtual std::string valueAsString(void * /* row */,
                                      contact * /* auth_user */) {
        return "invalid";
    }
    virtual ColumnType type() = 0;

    // TODO(sp) Get rid of the contact* paramter once IntColumn::getValue is
    // fixed, it is just an artifact.
    virtual void output(void *row, RowRenderer &r, contact *auth_user) = 0;

    virtual bool mustDelete() {
        return false;  // true for dynamic Columns to be deleted after Query
    }
    virtual Filter *createFilter(RelationalOperator, const std::string &);

    Logger *logger() const { return _logger; }

private:
    Logger *const _logger;
    std::string _name;
    std::string _description;
    int _indirect_offset;
    int _extra_offset;
    int _extra_extra_offset;
};

#endif  // Column_h
