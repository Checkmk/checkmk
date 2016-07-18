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

#include "CustomVarsColumn.h"
#include <string.h>
#include "CustomVarsFilter.h"
#include "Renderer.h"

using std::string;

CustomVarsColumn::CustomVarsColumn(string name, string description, int offset,
                                   int indirect_offset, Type what,
                                   int extra_offset)
    : Column(name, description, indirect_offset, extra_offset)
    , _what(what)
    , _offset(offset) {}

ColumnType CustomVarsColumn::type() {
    switch (_what) {
        case Type::varnames:
            return ColumnType::list;
        case Type::values:
            return ColumnType::list;
        case Type::dict:
            return ColumnType::dict;
    }
    return ColumnType::list;  // unreachable
}

void CustomVarsColumn::output(void *row, Renderer *renderer,
                              contact * /* auth_user */) {
    switch (_what) {
        case Type::varnames: {
            renderer->outputBeginList();
            bool first = true;
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (first) {
                    first = false;
                } else {
                    renderer->outputListSeparator();
                }
                renderer->outputString(cvm->variable_name);
            }
            renderer->outputEndList();
            break;
        }
        case Type::values: {
            renderer->outputBeginList();
            bool first = true;
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (first) {
                    first = false;
                } else {
                    renderer->outputListSeparator();
                }
                renderer->outputString(cvm->variable_value);
            }
            renderer->outputEndList();
            break;
        }
        case Type::dict: {
            renderer->outputBeginDict();
            bool first = true;
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (first) {
                    first = false;
                } else {
                    renderer->outputDictSeparator();
                }
                renderer->outputString(cvm->variable_name);
                renderer->outputDictValueSeparator();
                renderer->outputString(cvm->variable_value);
            }
            renderer->outputEndDict();
            break;
        }
    }
}

Filter *CustomVarsColumn::createFilter(RelationalOperator relOp,
                                       const string &value) {
    return new CustomVarsFilter(this, relOp, value);
}

customvariablesmember *CustomVarsColumn::getCVM(void *row) {
    void *data = shiftPointer(row);
    if (data == nullptr) {
        return nullptr;
    }
    return *reinterpret_cast<customvariablesmember **>(
        reinterpret_cast<char *>(data) + _offset);
}

bool CustomVarsColumn::contains(void *row, const string &value) {
    switch (_what) {
        case Type::varnames: {
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (value.compare(cvm->variable_name) == 0) {
                    return true;
                }
            }
            return false;
        }
        case Type::values: {
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (value.compare(cvm->variable_value) == 0) {
                    return true;
                }
            }
            return false;
        }
        case Type::dict: {
            for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
                 cvm = cvm->next) {
                if (value.compare(cvm->variable_value) == 0) {
                    return true;
                }
            }
            return false;
        }
    }
    return false;  // unreachable
}

string CustomVarsColumn::getVariable(void *row, const string &varname) {
    for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
         cvm = cvm->next) {
        if (varname.compare(cvm->variable_name) == 0) {
            return cvm->variable_value;
        }
    }
    return "";
}
