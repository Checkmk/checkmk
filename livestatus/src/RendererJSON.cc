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
class OutputBuffer;

using std::string;
using std::vector;

RendererJSON::RendererJSON(OutputBuffer &output, int timezone_offset,
                           Encoding data_encoding)
    : Renderer(output, timezone_offset, data_encoding) {}

// --------------------------------------------------------------------------

void RendererJSON::beginQuery() { add("["); }
void RendererJSON::separateQueryElements() { add(",\n"); }
void RendererJSON::endQuery() { add("]\n"); }

// --------------------------------------------------------------------------

void RendererJSON::beginRow() { add("["); }
void RendererJSON::beginRowElement() {}
void RendererJSON::endRowElement() {}
void RendererJSON::separateRowElements() { add(","); }
void RendererJSON::endRow() { add("]"); }

// --------------------------------------------------------------------------

void RendererJSON::beginList() { add("["); }
void RendererJSON::separateListElements() { add(","); }
void RendererJSON::endList() { add("]"); }

// --------------------------------------------------------------------------

void RendererJSON::beginSublist() { beginList(); }
void RendererJSON::separateSublistElements() { separateListElements(); }
void RendererJSON::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererJSON::beginDict() { add("{"); }
void RendererJSON::separateDictElements() { add(","); }
void RendererJSON::separateDictKeyValue() { add(":"); }
void RendererJSON::endDict() { add("}"); }

// --------------------------------------------------------------------------

void RendererJSON::outputNull() { add("null"); }

void RendererJSON::outputBlob(const vector<char> &value) {
    outputUnicodeString("", &value[0], &value[value.size()], Encoding::latin1);
}

void RendererJSON::outputString(const string &value) {
    outputUnicodeString("", &value[0], &value[value.size()], _data_encoding);
}
