// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDFetch_h
#define RRDFetch_h

#include <cassert>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <ios>
#include <string>
#include <system_error>
#include <vector>

class RRDFetchHeader {
    /*
     * FlushVersion: 1
     * Start: ...
     * End: ...
     * Step: ...
     * DSCount: 7
     */
    enum Field { FlushVersion, Start, End, Step, Dscount };
    using C = std::chrono::system_clock;

public:
    using time_point = C::time_point;
    explicit RRDFetchHeader(const std::vector<std::string> &h) : _h{h} {
        assert(h.size() == size());
    }
    static std::size_t size() { return Field::Dscount + 1; }
    [[nodiscard]] unsigned long flush_version() const {
        return parse(_h[Field::FlushVersion]);
    }
    [[nodiscard]] time_point start() const {
        return time_point{std::chrono::seconds{parse(_h[Field::Start])}};
    }
    [[nodiscard]] time_point end() const {
        return time_point{std::chrono::seconds{parse(_h[Field::End])}};
    }
    [[nodiscard]] unsigned long step() const { return parse(_h[Field::Step]); }
    [[nodiscard]] unsigned long dscount() const {
        return parse(_h[Field::Dscount]);
    }

private:
    std::vector<std::string> _h;
    [[nodiscard]] static unsigned long parse(const std::string &line) {
        const auto idx = line.find(": ");
        if (idx == std::string::npos) {
            return {};
        }
        unsigned long number = 0;
        // NOLINTBEGIN(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        auto [ptr, ec] =
            std::from_chars(line.data() + static_cast<std::size_t>(idx) + 2,
                            line.data() + line.size(), number);
        // NOLINTEND(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        return ec == std::errc{} ? number : 0;
    }
};

std::ostream &operator<<(std::ostream &os, const RRDFetchHeader &h);

struct RRDFetchBinPayloadHeader {
    // DSName-[DSNAME]: BinaryData [VALUE_COUNT] [VALUE_SIZE] [ENDIANNESS]
    static RRDFetchBinPayloadHeader parse(const std::string &line);
    [[nodiscard]] std::string unparse() const;
    std::size_t dsname;
    std::size_t value_count;
    std::size_t value_size;
    std::string endianness;
};

#endif
