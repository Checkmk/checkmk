// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDFetch.h"

#include <charconv>
#include <sstream>
#include <stdexcept>
#include <string_view>

#include "livestatus/StringUtils.h"

std::ostream &operator<<(std::ostream &os, const RRDFetchHeader &h) {
    return os << "FlushVersion: " << h.flush_version() << "\n"
              << "Start: " << std::chrono::system_clock::to_time_t(h.start())
              << "\n"
              << "End: " << std::chrono::system_clock::to_time_t(h.end())
              << "\n"
              << "Step: " << h.step() << "\n"
              << "DSCount: " << h.dscount() << "\n";
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
