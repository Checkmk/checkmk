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

#include "RendererJSON.h"

using std::string;
using std::vector;

RendererJSON::RendererJSON(OutputBuffer *output,
                           OutputBuffer::ResponseHeader response_header,
                           bool do_keep_alive, string invalid_header_message,
                           int timezone_offset)
    : Renderer(output, response_header, do_keep_alive, invalid_header_message,
               timezone_offset) {}

// --------------------------------------------------------------------------

void RendererJSON::startOfQuery() { add("["); }

void RendererJSON::outputDataSetSeparator() { add(",\n"); }

void RendererJSON::endOfQuery() { add("]\n"); }

// --------------------------------------------------------------------------

void RendererJSON::outputDatasetBegin() { add("["); }

void RendererJSON::outputFieldSeparator() { add(","); }

void RendererJSON::outputDatasetEnd() { add("]"); }

// --------------------------------------------------------------------------

void RendererJSON::outputBeginList() { add("["); }

void RendererJSON::outputListSeparator() { add(","); }

void RendererJSON::outputEndList() { add("]"); }

// --------------------------------------------------------------------------

void RendererJSON::outputBeginSublist() { add("["); }

void RendererJSON::outputSublistSeparator() { add(","); }

void RendererJSON::outputEndSublist() { add("]"); }

// --------------------------------------------------------------------------

void RendererJSON::outputBeginDict() { add("{"); }

void RendererJSON::outputDictSeparator() { add(","); }

void RendererJSON::outputDictValueSeparator() { add(":"); }

void RendererJSON::outputEndDict() { add("}"); }

// --------------------------------------------------------------------------

void RendererJSON::outputNull() { add("null"); }

void RendererJSON::outputBlob(const vector<char> *blob) {
    if (blob != nullptr) {
        outputString(&(*blob)[0], blob->size());
    } else {
        outputNull();
    }
}

void RendererJSON::outputString(const char *value, int len) {
    if (value == nullptr) {
        add("\"\"");
        return;
    }
    outputChars(value, len);
}
