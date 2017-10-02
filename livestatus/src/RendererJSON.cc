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
#include <ostream>
class Logger;

RendererJSON::RendererJSON(std::ostream &os, Logger *logger,
                           std::chrono::seconds timezone_offset,
                           Encoding data_encoding)
    : Renderer(os, logger, timezone_offset, data_encoding) {}

// --------------------------------------------------------------------------

void RendererJSON::beginQuery() { _os << "["; }
void RendererJSON::separateQueryElements() { _os << ",\n"; }
void RendererJSON::endQuery() { _os << "]\n"; }

// --------------------------------------------------------------------------

void RendererJSON::beginRow() { _os << "["; }
void RendererJSON::beginRowElement() {}
void RendererJSON::endRowElement() {}
void RendererJSON::separateRowElements() { _os << ","; }
void RendererJSON::endRow() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererJSON::beginList() { _os << "["; }
void RendererJSON::separateListElements() { _os << ","; }
void RendererJSON::endList() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererJSON::beginSublist() { beginList(); }
void RendererJSON::separateSublistElements() { separateListElements(); }
void RendererJSON::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererJSON::beginDict() { _os << "{"; }
void RendererJSON::separateDictElements() { _os << ","; }
void RendererJSON::separateDictKeyValue() { _os << ":"; }
void RendererJSON::endDict() { _os << "}"; }

// --------------------------------------------------------------------------

void RendererJSON::outputNull() { _os << "null"; }

void RendererJSON::outputBlob(const std::vector<char> &value) {
    outputUnicodeString("", &value[0], &value[value.size()], Encoding::latin1);
}

void RendererJSON::outputString(const std::string &value) {
    outputUnicodeString("", &value[0], &value[value.size()], _data_encoding);
}
