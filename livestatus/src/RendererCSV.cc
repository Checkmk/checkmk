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

#include "RendererCSV.h"
#include <algorithm>

using std::move;
using std::string;
using std::vector;

RendererCSV::RendererCSV(OutputBuffer *output,
                         OutputBuffer::ResponseHeader response_header,
                         bool do_keep_alive, string invalid_header_message,
                         string field_separator, string dataset_separator,
                         string list_separator, string host_service_separator,
                         int timezone_offset)
    : Renderer(output, response_header, do_keep_alive, invalid_header_message,
               timezone_offset)
    , _field_separator(move(field_separator))
    , _dataset_separator(move(dataset_separator))
    , _list_separator(move(list_separator))
    , _host_service_separator(move(host_service_separator)) {}

// --------------------------------------------------------------------------

void RendererCSV::startOfQuery() {}

void RendererCSV::outputDataSetSeparator() {}

void RendererCSV::endOfQuery() {}

// --------------------------------------------------------------------------

void RendererCSV::outputDatasetBegin() {}

void RendererCSV::outputFieldSeparator() { add(_field_separator); }

void RendererCSV::outputDatasetEnd() { add(_dataset_separator); }

// --------------------------------------------------------------------------

void RendererCSV::outputBeginList() {}

void RendererCSV::outputListSeparator() { add(_list_separator); }

void RendererCSV::outputEndList() {}

// --------------------------------------------------------------------------

void RendererCSV::outputBeginSublist() {}

void RendererCSV::outputSublistSeparator() { add(_host_service_separator); }

void RendererCSV::outputEndSublist() {}

// --------------------------------------------------------------------------

void RendererCSV::outputBeginDict() {}

void RendererCSV::outputDictSeparator() { add(_list_separator); }

void RendererCSV::outputDictValueSeparator() { add(_host_service_separator); }

void RendererCSV::outputEndDict() {}

// --------------------------------------------------------------------------

void RendererCSV::outputNull() {}

void RendererCSV::outputBlob(const vector<char> *blob) {
    if (blob != nullptr) {
        add(*blob);
    }
}

void RendererCSV::outputString(const char *value, int /* len */) {
    if (value == nullptr) {
        return;
    }
    add(value);
}
