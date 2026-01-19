// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDFetch.h"

#include <cassert>
#include <charconv>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <system_error>

#include "livestatus/StringUtils.h"

using namespace std::string_literals;

namespace {
[[nodiscard]] unsigned long get_header_value(std::string_view line) {
    // "KEY: VALUE" -> VALUE
    const std::size_t idx = line.find(": ");
    if (idx == std::string::npos) {
        return {};
    }
    unsigned long number = 0;
    auto [ptr, ec] =
        // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        std::from_chars(line.begin() + idx + 2, line.end(), number);
    return ec == std::errc{} ? number : 0;
}
}  // namespace

RRDFetchHeader RRDFetchHeader::parse(const std::vector<std::string> &h) {
    assert(h.size() == size());
    return RRDFetchHeader{
        .flush_version = get_header_value(h[Field::FlushVersion]),
        .start = RRDFetchHeader::time_point{std::chrono::seconds{
            get_header_value(h[Field::Start])}},
        .end = RRDFetchHeader::time_point{std::chrono::seconds{
            get_header_value(h[Field::End])}},
        .step = get_header_value(h[Field::Step]),
        .dscount = get_header_value(h[Field::Dscount]),
    };
}

std::vector<std::string> RRDFetchHeader::unparse() const {
    return std::vector<std::string>{
        "FlushVersion: "s + std::to_string(flush_version),
        "Start: "s +
            std::to_string(std::chrono::system_clock::to_time_t(start)),
        "End: "s + std::to_string(std::chrono::system_clock::to_time_t(end)),
        "Step: "s + std::to_string(step),
        "DSCount: "s + std::to_string(dscount),
    };
}

namespace {
[[nodiscard]] std::size_t from_chars(std::string_view str) {
    std::size_t value = 0;
    auto [ptr, ec] = std::from_chars(str.begin(), str.end(), value);
    if (ec != std::errc{} && ptr != str.end()) {
        throw std::runtime_error("invalid header");
    }
    return value;
}
}  // namespace

RRDFetchBinPayloadHeader RRDFetchBinPayloadHeader::parse(
    const std::string &line) {
    const auto vec = mk::split(line, ' ');
    if (vec.size() != 5) {
        throw std::runtime_error("invalid header");
    }
    const auto name = mk::split(vec[0], '-');
    if (name.size() != 2) {
        throw std::runtime_error("invalid header");
    }
    return RRDFetchBinPayloadHeader{
        .dsname = from_chars(name[1]),
        .value_count = from_chars(vec[2]),
        .value_size = from_chars(vec[3]),
        .endianness = mk::rstrip(vec[4]),
    };
}

std::string RRDFetchBinPayloadHeader::unparse() const {
    std::ostringstream os{};
    os << "DSName-" << dsname << " BinaryData " << value_count << " "
       << value_size << " " << endianness;
    return os.str();
}
