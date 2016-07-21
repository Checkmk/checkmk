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
                         CSVSeparators separators, int timezone_offset)
    : Renderer(output, response_header, do_keep_alive, invalid_header_message,
               timezone_offset)
    , _separators(move(separators)) {}

// --------------------------------------------------------------------------

void RendererCSV::startQuery() {}
void RendererCSV::separateQueryElements() {}
void RendererCSV::endQuery() {}

// --------------------------------------------------------------------------

void RendererCSV::startRow() {}
void RendererCSV::separateRowElements() { add(_separators.field()); }
void RendererCSV::endRow() { add(_separators.dataset()); }

// --------------------------------------------------------------------------

void RendererCSV::startList() {}
void RendererCSV::separateListElements() { add(_separators.list()); }
void RendererCSV::endList() {}

// --------------------------------------------------------------------------

void RendererCSV::startSublist() {}
void RendererCSV::separateSublistElements() { add(_separators.hostService()); }
void RendererCSV::endSublist() {}

// --------------------------------------------------------------------------

void RendererCSV::startDict() {}
void RendererCSV::separateDictElements() { add(_separators.list()); }
void RendererCSV::separateDictKeyValue() { add(_separators.hostService()); }
void RendererCSV::endDict() {}

// --------------------------------------------------------------------------

void RendererCSV::outputNull() {}

void RendererCSV::outputBlob(const vector<char> &value) { add(value); }

void RendererCSV::outputString(const string &value) { add(value); }
