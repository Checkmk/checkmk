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
#include <ostream>
class Logger;

RendererPython3::RendererPython3(std::ostream &os, Logger *logger,
                                 std::chrono::seconds timezone_offset,
                                 Encoding data_encoding)
    : Renderer(os, logger, timezone_offset, data_encoding) {}

// --------------------------------------------------------------------------

void RendererPython3::beginQuery() { _os << "["; }
void RendererPython3::separateQueryElements() { _os << ",\n"; }
void RendererPython3::endQuery() { _os << "]\n"; }

// --------------------------------------------------------------------------

void RendererPython3::beginRow() { _os << "["; }
void RendererPython3::beginRowElement() {}
void RendererPython3::endRowElement() {}
void RendererPython3::separateRowElements() { _os << ","; }
void RendererPython3::endRow() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererPython3::beginList() { _os << "["; }
void RendererPython3::separateListElements() { _os << ","; }
void RendererPython3::endList() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererPython3::beginSublist() { beginList(); }
void RendererPython3::separateSublistElements() { separateListElements(); }
void RendererPython3::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererPython3::beginDict() { _os << "{"; }
void RendererPython3::separateDictElements() { _os << ","; }
void RendererPython3::separateDictKeyValue() { _os << ":"; }
void RendererPython3::endDict() { _os << "}"; }

// --------------------------------------------------------------------------

void RendererPython3::outputNull() { _os << "None"; }

void RendererPython3::outputBlob(const std::vector<char> &value) {
    outputByteString("b", value);
}

void RendererPython3::outputString(const std::string &value) {
    outputUnicodeString("", &value[0], &value[value.size()], _data_encoding);
}
