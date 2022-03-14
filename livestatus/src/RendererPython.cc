// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "RendererPython.h"

#include <ostream>
class Logger;

RendererPython::RendererPython(std::ostream &os, Logger *logger,
                               Encoding data_encoding)
    : Renderer(os, logger, data_encoding) {}

// --------------------------------------------------------------------------

void RendererPython::beginQuery() { _os << "["; }
void RendererPython::separateQueryElements() { _os << ",\n"; }
void RendererPython::endQuery() { _os << "]\n"; }

// --------------------------------------------------------------------------

void RendererPython::beginRow() { _os << "["; }
void RendererPython::beginRowElement() {}
void RendererPython::endRowElement() {}
void RendererPython::separateRowElements() { _os << ","; }
void RendererPython::endRow() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererPython::beginList() { _os << "["; }
void RendererPython::separateListElements() { _os << ","; }
void RendererPython::endList() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererPython::beginSublist() { beginList(); }
void RendererPython::separateSublistElements() { separateListElements(); }
void RendererPython::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererPython::beginDict() { _os << "{"; }
void RendererPython::separateDictElements() { _os << ","; }
void RendererPython::separateDictKeyValue() { _os << ":"; }
void RendererPython::endDict() { _os << "}"; }

// --------------------------------------------------------------------------

void RendererPython::outputNull() { _os << "None"; }

void RendererPython::outputBlob(const std::vector<char> &value) {
    outputByteString("b", value);
}

void RendererPython::outputString(const std::string &value) {
    outputUnicodeString("u", &value[0], &value[value.size()], _data_encoding);
}
