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

#include "Renderer.h"
#include <cmath>
#include <iomanip>
#include <ostream>
#include "Logger.h"
#include "RendererBrokenCSV.h"
#include "RendererCSV.h"
#include "RendererJSON.h"
#include "RendererPython.h"
#include "RendererPython3.h"

using std::chrono::system_clock;
using std::hex;
using std::make_unique;
using std::ostringstream;
using std::setfill;
using std::setw;
using std::size_t;
using std::string;
using std::unique_ptr;
using std::vector;

Renderer::Renderer(OutputBuffer &output,
                   OutputBuffer::ResponseHeader response_header,
                   bool do_keep_alive, string invalid_header_message,
                   int timezone_offset, Encoding data_encoding)
    : _data_encoding(data_encoding)
    , _output(output)
    , _timezone_offset(timezone_offset)
    , _logger(output.getLogger()) {
    _output.setResponseHeader(response_header);
    _output.setDoKeepalive(do_keep_alive);
    if (invalid_header_message != "") {
        _output.setError(OutputBuffer::ResponseCode::invalid_header,
                         invalid_header_message);
    }
}

Renderer::~Renderer() = default;

// static
unique_ptr<Renderer> Renderer::make(
    OutputFormat format, OutputBuffer &output,
    OutputBuffer::ResponseHeader response_header, bool do_keep_alive,
    string invalid_header_message, const CSVSeparators &separators,
    int timezone_offset, Encoding data_encoding) {
    switch (format) {
        case OutputFormat::csv:
            return make_unique<RendererCSV>(
                output, response_header, do_keep_alive, invalid_header_message,
                timezone_offset, data_encoding);
        case OutputFormat::broken_csv:
            return make_unique<RendererBrokenCSV>(
                output, response_header, do_keep_alive, invalid_header_message,
                separators, timezone_offset, data_encoding);
        case OutputFormat::json:
            return make_unique<RendererJSON>(
                output, response_header, do_keep_alive, invalid_header_message,
                timezone_offset, data_encoding);
        case OutputFormat::python:
            return make_unique<RendererPython>(
                output, response_header, do_keep_alive, invalid_header_message,
                timezone_offset, data_encoding);
        case OutputFormat::python3:
            return make_unique<RendererPython3>(
                output, response_header, do_keep_alive, invalid_header_message,
                timezone_offset, data_encoding);
    }
    return nullptr;  // unreachable
}

void Renderer::setError(OutputBuffer::ResponseCode code,
                        const string &message) {
    _output.setError(code, message);
}

size_t Renderer::size() const { return _output.size(); }

void Renderer::add(const string &str) { _output.add(str); }

void Renderer::add(const vector<char> &value) { _output.add(value); }

void Renderer::output(double value) {
    // Funny cast for older non-C++11 headers
    if (static_cast<bool>(std::isnan(value))) {
        output(Null());
    } else {
        ostringstream os;
        os << value;
        add(os.str());
    }
}

void Renderer::output(PlainChar value) { add(string(1, value._ch)); }

void Renderer::output(HexEscape value) {
    ostringstream os;
    os << R"(\x)" << hex << setw(2) << setfill('0')
       << static_cast<unsigned>(static_cast<unsigned char>(value._ch));
    add(os.str());
}

void Renderer::output(char16_t value) {
    ostringstream os;
    os << R"(\u)" << hex << setw(4) << setfill('0') << value;
    add(os.str());
}

void Renderer::output(char32_t value) {
    if (value < 0x10000) {
        output(char16_t(value));
    } else {
        // we need a surrogate pair
        char32_t offs = value - 0x10000;
        output(char16_t(((offs >> 10) & 0x3FF) + 0xD800));
        output(char16_t((offs & 0x3FF) + 0xDC00));
    }
}

void Renderer::output(Null /* unused */) { outputNull(); }

void Renderer::output(const vector<char> &value) { outputBlob(value); }

void Renderer::output(const string &value) { outputString(value); }

void Renderer::output(system_clock::time_point value) {
    output(system_clock::to_time_t(value) + _timezone_offset);
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

void Renderer::outputByteString(const string &prefix,
                                const vector<char> &value) {
    add(prefix);
    add(R"(")");  // "
    for (auto ch : value) {
        if (isBoringChar(ch)) {
            output(PlainChar{ch});
        } else {
            output(HexEscape{ch});
        }
    }
    add(R"(")");  // "
}

void Renderer::outputUnicodeString(const string &prefix, const char *start,
                                   const char *end, Encoding data_encoding) {
    add(prefix);
    add(R"(")");  // "
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
    add(R"(")");  // "
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
            if ((ch2 & 0xC0) != 0x80) {
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
