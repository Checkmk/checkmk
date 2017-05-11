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
#include <ostream>
class Logger;

using std::ostream;
using std::string;
using std::vector;

RendererCSV::RendererCSV(ostream &os, Logger *logger, int timezone_offset,
                         Encoding data_encoding)
    : Renderer(os, logger, timezone_offset, data_encoding) {}

// --------------------------------------------------------------------------

void RendererCSV::beginQuery() {}
void RendererCSV::separateQueryElements() {}
void RendererCSV::endQuery() {}

// --------------------------------------------------------------------------

void RendererCSV::beginRow() {}
void RendererCSV::beginRowElement() { _os << R"(")"; }  // "
void RendererCSV::endRowElement() { _os << R"(")"; }    // "
void RendererCSV::separateRowElements() { _os << ","; }
void RendererCSV::endRow() { _os << "\r\n"; }

// --------------------------------------------------------------------------

void RendererCSV::beginList() {}
void RendererCSV::separateListElements() { _os << ","; }
void RendererCSV::endList() {}

// --------------------------------------------------------------------------

void RendererCSV::beginSublist() {}
void RendererCSV::separateSublistElements() { _os << "|"; }
void RendererCSV::endSublist() {}

// --------------------------------------------------------------------------

void RendererCSV::beginDict() {}
void RendererCSV::separateDictElements() { _os << ","; }
void RendererCSV::separateDictKeyValue() { _os << "|"; }
void RendererCSV::endDict() {}

// --------------------------------------------------------------------------

void RendererCSV::outputNull() {}

void RendererCSV::outputEscaped(char ch) {
    _os << (ch == '"' ? R"("")" : string(1, ch));
}

void RendererCSV::outputBlob(const vector<char> &value) {
    for (auto ch : value) {
        outputEscaped(ch);
    }
}

void RendererCSV::outputString(const string &value) {
    for (auto ch : value) {
        outputEscaped(ch);
    }
}
