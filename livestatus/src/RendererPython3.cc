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

#include "RendererPython3.h"

using std::string;
using std::vector;

RendererPython3::RendererPython3(OutputBuffer *output,
                                 OutputBuffer::ResponseHeader response_header,
                                 bool do_keep_alive,
                                 string invalid_header_message,
                                 int timezone_offset)
    : Renderer(output, response_header, do_keep_alive, invalid_header_message,
               timezone_offset) {}

// --------------------------------------------------------------------------

void RendererPython3::startQuery() { add("["); }
void RendererPython3::separateQueryElements() { add(",\n"); }
void RendererPython3::endQuery() { add("]\n"); }

// --------------------------------------------------------------------------

void RendererPython3::startRow() { add("["); }
void RendererPython3::separateRowElements() { add(","); }
void RendererPython3::endRow() { add("]"); }

// --------------------------------------------------------------------------

void RendererPython3::startList() { add("["); }
void RendererPython3::separateListElements() { add(","); }
void RendererPython3::endList() { add("]"); }

// --------------------------------------------------------------------------

void RendererPython3::startSublist() { startList(); }
void RendererPython3::separateSublistElements() { separateListElements(); }
void RendererPython3::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererPython3::startDict() { add("{"); }
void RendererPython3::separateDictElements() { add(","); }
void RendererPython3::separateDictKeyValue() { add(":"); }
void RendererPython3::endDict() { add("}"); }

// --------------------------------------------------------------------------

void RendererPython3::outputNull() { add("None"); }

void RendererPython3::outputBlob(const vector<char> &value) {
    add("b\"");
    for (unsigned char ch : value) {
        add(ch < 32 || ch > 127 || ch == '"' || ch == '\\' ? unicodeEscape(ch)
                                                           : string(1, ch));
    }
    add("\"");
}

void RendererPython3::outputString(const string &value) {
    add("\"");
    outputCharsAsString(value);
    add("\"");
}
