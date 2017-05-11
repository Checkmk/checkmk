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

#include "RendererBrokenCSV.h"
#include <ostream>

using std::string;
using std::vector;

// --------------------------------------------------------------------------

void RendererBrokenCSV::beginQuery() {}
void RendererBrokenCSV::separateQueryElements() {}
void RendererBrokenCSV::endQuery() {}

// --------------------------------------------------------------------------

void RendererBrokenCSV::beginRow() {}
void RendererBrokenCSV::beginRowElement() {}
void RendererBrokenCSV::endRowElement() {}
void RendererBrokenCSV::separateRowElements() { _os << _separators.field(); }
void RendererBrokenCSV::endRow() { _os << _separators.dataset(); }

// --------------------------------------------------------------------------

void RendererBrokenCSV::beginList() {}
void RendererBrokenCSV::separateListElements() { _os << _separators.list(); }
void RendererBrokenCSV::endList() {}

// --------------------------------------------------------------------------

void RendererBrokenCSV::beginSublist() {}
void RendererBrokenCSV::separateSublistElements() {
    _os << _separators.hostService();
}
void RendererBrokenCSV::endSublist() {}

// --------------------------------------------------------------------------

void RendererBrokenCSV::beginDict() {}
void RendererBrokenCSV::separateDictElements() { _os << _separators.list(); }
void RendererBrokenCSV::separateDictKeyValue() {
    _os << _separators.hostService();
}
void RendererBrokenCSV::endDict() {}

// --------------------------------------------------------------------------

void RendererBrokenCSV::outputNull() {}

void RendererBrokenCSV::outputBlob(const vector<char> &value) {
    _os.write(&value[0], value.size());
}

void RendererBrokenCSV::outputString(const string &value) { _os << value; }
