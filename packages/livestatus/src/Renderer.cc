// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Renderer.h"

#include <cmath>
#include <cstdint>

#include "livestatus/Logger.h"
#include "livestatus/RendererBrokenCSV.h"
#include "livestatus/RendererCSV.h"
#include "livestatus/RendererJSON.h"
#include "livestatus/RendererPython3.h"
#include "livestatus/data_encoding.h"

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
        case OutputFormat::python3:
            return std::make_unique<RendererPython3>(os, logger, data_encoding);
    }
    return nullptr;  // unreachable
}

void Renderer::output(double value) {
    if (std::isnan(value)) {
        output(Null());
    } else {
        _os << value;
    }
}

void Renderer::output(const RowFragment &value) { _os << value._str; }

void Renderer::outputUnicodeChar(char32_t value) {
    const uint_least32_t number{value};
    if (number < 0x10000U) {
        outputHex('u', 4, number);
    } else if (useSurrogatePairs()) {
        outputHex('u', 4, 0xd800U | (((number - 0x10000U) >> 10) & 0x3ffU));
        outputHex('u', 4, 0xdc00U | ((number - 0x10000U) & 0x3ffU));
    } else {
        outputHex('U', 8, number);
    }
}

void Renderer::output(Null /* unused */) { outputNull(); }

void Renderer::output(const std::vector<char> &value) { outputBlob(value); }

void Renderer::output(const std::string &value) { outputString(value); }

void Renderer::output(std::chrono::system_clock::time_point value) {
    output(std::chrono::system_clock::to_time_t(value));
}

void Renderer::output(CommentType value) { _os << static_cast<int32_t>(value); }

void Renderer::output(RecurringKind value) {
    _os << static_cast<int32_t>(value);
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
    Warning(_logger) << "invalid byte " << static_cast<int>(ch)
                     << " in UTF-8 sequence";
}

void Renderer::outputByteString(const std::string &prefix,
                                const std::vector<char> &value) {
    _os << prefix << R"(")";  // "
    for (auto ch : value) {
        if (isBoringChar(ch)) {
            _os.put(ch);
        } else {
            outputHex('x', 2,
                      static_cast<unsigned>(static_cast<unsigned char>(ch)));
        }
    }
    _os << R"(")";  // "
}

void Renderer::outputUnicodeString(const char *start, const char *end,
                                   Encoding data_encoding) {
    _os << R"(")";  // "
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

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
void Renderer::outputUTF8(const char *start, const char *end) {
    // NOLINTBEGIN(cppcoreguidelines-pro-bounds-pointer-arithmetic)
    for (const char *p = start; p != end; ++p) {
        const unsigned char ch0 = *p;
        if ((ch0 & 0x80) == 0x00) {
            if (isBoringChar(ch0)) {
                _os.put(*p);
            } else {
                outputUnicodeChar(ch0);
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
            const unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            outputUnicodeChar(((ch0 & 0x1F) << 6) |  //
                              ((ch1 & 0x3F) << 0));
        } else if ((ch0 & 0xF0) == 0xE0) {
            // 3 byte encoding
            if (end <= &p[2]) {
                return truncatedUTF8();
            }
            const unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            const unsigned char ch2 = *++p;
            if ((ch2 & 0xC0) != 0x80) {
                return invalidUTF8(ch2);
            }
            outputUnicodeChar(((ch0 & 0x0F) << 12) |  //
                              ((ch1 & 0x3F) << 6) |   //
                              ((ch2 & 0x3F) << 0));
        } else if ((ch0 & 0xF8) == 0xF0) {
            // 4 byte encoding
            if (ch0 == 0xF5 || ch0 == 0xF6 || ch0 == 0xF7) {
                // result would be larger than 0x10FFFF
                return invalidUTF8(ch0);
            }
            if (end <= &p[3]) {
                return truncatedUTF8();
            }
            const unsigned char ch1 = *++p;
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            const unsigned char ch2 = *++p;
            if ((ch2 & 0xC0) != 0x80) {
                return invalidUTF8(ch2);
            }
            const unsigned char ch3 = *++p;
            if ((ch3 & 0xC0) != 0x80) {
                return invalidUTF8(ch3);
            }
            outputUnicodeChar(((ch0 & 0x07) << 18) |  //
                              ((ch1 & 0x3F) << 12) |  //
                              ((ch2 & 0x3f) << 6) |   //
                              ((ch3 & 0x3f) << 0));
        } else {
            return invalidUTF8(ch0);
        }
    }
}

void Renderer::outputLatin1(const char *start, const char *end) {
    for (const char *p = start; p != end; ++p) {
        const unsigned char ch = *p;
        if (isBoringChar(ch)) {
            _os.put(*p);
        } else {
            outputUnicodeChar(ch);
        }
    }
}

void Renderer::outputMixed(const char *start, const char *end) {
    for (const char *p = start; p != end; ++p) {
        const unsigned char ch0 = *p;
        if (isBoringChar(ch0)) {
            _os.put(*p);
        } else if ((ch0 & 0xE0) == 0xC0) {
            // Possible 2 byte encoding? => Assume UTF-8, ignore overlong
            // encodings
            if (end <= &p[1]) {
                return truncatedUTF8();
            }
            const unsigned char ch1 = *++p;
            // NOLINTEND(cppcoreguidelines-pro-bounds-pointer-arithmetic)
            if ((ch1 & 0xC0) != 0x80) {
                return invalidUTF8(ch1);
            }
            outputUnicodeChar(((ch0 & 0x1F) << 6) |  //
                              ((ch1 & 0x3F) << 0));
        } else {
            // Assume Latin1.
            outputUnicodeChar(ch0);
        }
    }
}
