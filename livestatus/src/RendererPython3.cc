// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "RendererPython3.h"

#include <ostream>
class Logger;

RendererPython3::RendererPython3(std::ostream &os, Logger *logger,
                                 Encoding data_encoding)
    : Renderer(os, logger, data_encoding) {}

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
    outputUnicodeString("u", &value[0], &value[value.size()], _data_encoding);
}
