// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Renderer.h"

#include <cmath>
#include <cstdint>
#include <ctime>
#include <iomanip>
#include <ostream>

#include "Logger.h"
#include "OStreamStateSaver.h"
#include "RendererBrokenCSV.h"
#include "RendererCSV.h"
#include "RendererJSON.h"
#include "RendererPython.h"
#include "RendererPython3.h"
#include "data_encoding.h"

// static
std::unique_ptr<Renderer> Renderer::make(OutputFormat format, std::ostream &os,
                                         Logger *logger,
                                         const CSVSeparators &separators,
                                         Encoding data_encoding) {
    switch (format) {
        case OutputFormat::csv:
            return std::make_unique<RendererCSV>(os, logger, data_encoding);
        case OutputFormat::broken_csv:
            return std::make_unique<RendererBrokenCSV>(os, logger, separators,
                                                       data_encoding);
        case OutputFormat::json:
            return std::make_unique<RendererJSON>(os, logger, data_encoding);
        case OutputFormat::python:
            return std::make_unique<RendererPython>(os, logger, data_encoding);
        case OutputFormat::python3:
            return std::make_unique<RendererPython3>(os, logger, data_encoding);
    }
    return nullptr;  // unreachable
}

void Renderer::output(double value) {
    // Funny cast for older non-C++11 headers
    if (static_cast<bool>(std::isnan(value))) {
        output(Null());
    } else {
        _os << value;
    }
}

void Renderer::output(PlainChar value) { _os.put(value._ch); }

void Renderer::output(HexEscape value) {
    OStreamStateSaver s(_os);
    _os << R"(\x)" << std::hex << std::setw(2) << std::setfill('0')
        << static_cast<unsigned>(static_cast<unsigned char>(value._ch));
}

void Renderer::output(const RowFragment &value) { _os << value._str; }

void Renderer::output(char16_t value) {
    OStreamStateSaver s(_os);
    _os << R"(\u)" << std::hex << std::setw(4) << std::setfill('0')
        << static_cast<uint16_t>(value);
}

void Renderer::output(char32_t value) {
    if (value < 0x10000) {
        output(char16_t(value));
    } else {
        OStreamStateSaver s(_os);
        _os << R"(\U)" << std::hex << std::setw(8) << std::setfill('0')
            << static_cast<uint32_t>(value);
    }
}

void Renderer::output(Null /* unused */) { outputNull(); }

void Renderer::output(const std::vector<char> &value) { outputBlob(value); }

void Renderer::output(const std::string &value) { outputString(value); }

void Renderer::output(std::chrono::system_clock::time_point value) {
    output(std::chrono::system_clock::to_time_t(value));
}

namespace {
bool isBoringChar(unsigned char ch) {
    return 32 <= ch && ch <= 127 && ch != '"' && ch != '\\';
}

}  // namespace

void Renderer::truncatedUTF8() {
    Warning(_logger) << "UTF-8 sequence too short";
}

void Renderer::invalidUTF8(unsigned char ch) {
    Warning(_logger) << "invalid byte " << int(ch) << " in UTF-8 sequence";
}

void Renderer::outputByteString(const std::string &prefix,
                                const std::vector<char> &value) {
    _os << prefix << R"(")";  // "
    for (auto ch : value) {
        if (isBoringChar(ch)) {
            output(PlainChar{ch});
        } else {
            output(HexEscape{ch});
        }
    }
    _os << R"(")";  // "
}

void Renderer::outputUnicodeString(const std::string &prefix, const char *start,
                                   const char *end, Encoding data_encoding) {
    _os << prefix << R"(")";  // "
    // TODO(sp) Use polymorphism instead of switch.
    // TODO(sp) Use codecvt framework instead of homemade stuff.
    switch (data_encoding) {
        case Encoding::utf8:
            outputUTF8(start, end);
            break;
        case Encoding::latin1:
            outputLatin1(start, end);
            break;
        case Encoding::mixed:
            outputMixed(start, end);
            break;
    }
    _os << R"(")";  // "
}

void Renderer::outputUTF8(const char *start, const char *end) {
    for (const char *p = start; p != end; ++p) {
        unsigned char ch0 = *p;
        if ((ch0 & 0x80) == 0x00) {
            if (isBoringChar(ch0)) {
                output(PlainChar{*p});
            } else {
                output(char32_t{ch0});
            }
        } else if ((ch0 & 0xE0) == 0xC0) {
            // 2 byte encoding
            if (ch0 == 0xC0 || ch0 == 0xC1) {
                // overlong encoding
                return invalidUTF8(ch0);
            }
            if (end <= &p[1]) {
                return truncatedUTF8();
            }
            unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            output(char32_t(((ch0 & 0x1F) << 6) |  //
                            ((ch1 & 0x3F) << 0)));
        } else if ((ch0 & 0xF0) == 0xE0) {
            // 3 byte encoding
            if (end <= &p[2]) {
                return truncatedUTF8();
            }
            unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            unsigned char ch2 = *++p;
            if ((ch2 & 0xC0) != 0x80) {
                return invalidUTF8(ch2);
            }
            output(char32_t(((ch0 & 0x0F) << 12) |  //
                            ((ch1 & 0x3F) << 6) |   //
                            ((ch2 & 0x3F) << 0)));
        } else if ((ch0 & 0xF8) == 0xF0) {
            // 4 byte encoding
            if (ch0 == 0xF5 || ch0 == 0xF6 || ch0 == 0xF7) {
                // result would be larger than 0x10FFFF
                return invalidUTF8(ch0);
            }
            if (end <= &p[3]) {
                return truncatedUTF8();
            }
            unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            unsigned char ch2 = *++p;
            if ((ch2 & 0xC0) != 0x80) {
                return invalidUTF8(ch2);
            }
            unsigned char ch3 = *++p;
            if ((ch3 & 0xC0) != 0x80) {
                return invalidUTF8(ch3);
            }
            output(char32_t(((ch0 & 0x07) << 18) |  //
                            ((ch1 & 0x3F) << 12) |  //
                            ((ch2 & 0x3f) << 6) |   //
                            ((ch3 & 0x3f) << 0)));
        } else {
            return invalidUTF8(ch0);
        }
    }
}

void Renderer::outputLatin1(const char *start, const char *end) {
    for (const char *p = start; p != end; ++p) {
        unsigned char ch = *p;
        if (isBoringChar(ch)) {
            output(PlainChar{*p});
        } else {
            output(char32_t{ch});
        }
    }
}

void Renderer::outputMixed(const char *start, const char *end) {
    for (const char *p = start; p != end; ++p) {
        unsigned char ch0 = *p;
        if (isBoringChar(ch0)) {
            output(PlainChar{*p});
        } else if ((ch0 & 0xE0) == 0xC0) {
            // Possible 2 byte encoding? => Assume UTF-8, ignore overlong
            // encodings
            if (end <= &p[1]) {
                return truncatedUTF8();
            }
            unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            output(char32_t(((ch0 & 0x1F) << 6) |  //
                            ((ch1 & 0x3F) << 0)));
        } else {
            // Assume Latin1.
            output(char32_t{ch0});
        }
    }
}
