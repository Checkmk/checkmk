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

#include "RendererPython.h"

using std::string;
using std::vector;

RendererPython::RendererPython(OutputBuffer &output,
                               OutputBuffer::ResponseHeader response_header,
                               bool do_keep_alive,
                               string invalid_header_message,
                               int timezone_offset, Encoding data_encoding)
    : Renderer(output, response_header, do_keep_alive, invalid_header_message,
               timezone_offset, data_encoding) {}

// --------------------------------------------------------------------------

void RendererPython::beginQuery() { add("["); }
void RendererPython::separateQueryElements() { add(",\n"); }
void RendererPython::endQuery() { add("]\n"); }

// --------------------------------------------------------------------------

void RendererPython::beginRow() { add("["); }
void RendererPython::beginRowElement() {}
void RendererPython::endRowElement() {}
void RendererPython::separateRowElements() { add(","); }
void RendererPython::endRow() { add("]"); }

// --------------------------------------------------------------------------

void RendererPython::beginList() { add("["); }
void RendererPython::separateListElements() { add(","); }
void RendererPython::endList() { add("]"); }

// --------------------------------------------------------------------------

void RendererPython::beginSublist() { beginList(); }
void RendererPython::separateSublistElements() { separateListElements(); }
void RendererPython::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererPython::beginDict() { add("{"); }
void RendererPython::separateDictElements() { add(","); }
void RendererPython::separateDictKeyValue() { add(":"); }
void RendererPython::endDict() { add("}"); }

// --------------------------------------------------------------------------

void RendererPython::outputNull() { add("None"); }

void RendererPython::outputBlob(const vector<char> &value) {
    outputByteString("", value);
}

void RendererPython::outputString(const string &value) {
    outputUnicodeString("u", &value[0], &value[value.size()], _data_encoding);
}
