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

#include "DynamicLogwatchFileColumn.h"
#include <stdexcept>
#include "Column.h"
#include "HostFileColumn.h"
#include "MonitoringCore.h"

namespace {
// Replace \\ with \ and \s with space
std::string unescape_filename(const std::string &filename) {
    std::string filename_native;
    bool quote_active = false;
    for (auto c : filename) {
        if (quote_active) {
            if (c == 's') {
                filename_native += ' ';
            } else {
                filename_native += c;
            }
            quote_active = false;
        } else if (c == '\\') {
            quote_active = true;
        } else {
            filename_native += c;
        }
    }
    return filename_native;
}
}  // namespace

std::unique_ptr<Column> DynamicLogwatchFileColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    // arguments contains a file name
    if (arguments.empty()) {
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': missing file name");
    }
    if (arguments.find('/') != std::string::npos) {
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': file name '" + arguments +
                                 "' contains slash");
    }
    auto mc = _mc;
    auto suffix = "/" + unescape_filename(arguments);
    return std::make_unique<HostFileColumn>(
        name, "Contents of logwatch file", _indirect_offset, _extra_offset, -1,
        0, [mc]() { return mc->mkLogwatchPath(); }, suffix);
}
