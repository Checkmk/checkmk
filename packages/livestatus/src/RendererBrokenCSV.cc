// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RendererBrokenCSV.h"

#include <ostream>
#include <vector>

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

bool RendererBrokenCSV::useSurrogatePairs() const { return false; };

void RendererBrokenCSV::outputNull() {}

void RendererBrokenCSV::outputBlob(const std::vector<char> &value) {
    // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
    _os.write(value.data(), value.size());
}

void RendererBrokenCSV::outputString(const std::string &value) { _os << value; }
