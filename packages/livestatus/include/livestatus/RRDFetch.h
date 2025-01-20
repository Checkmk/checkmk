// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDFetch_h
#define RRDFetch_h

#include <chrono>
#include <cstddef>
#include <string>
#include <vector>

struct RRDFetchHeader {
    /*
     * FlushVersion: 1
     * Start: ...
     * End: ...
     * Step: ...
     * DSCount: 7
     */
    [[nodiscard]] RRDFetchHeader static parse(
        const std::vector<std::string> &h);
    [[nodiscard]] std::vector<std::string> unparse() const;
    enum Field { FlushVersion, Start, End, Step, Dscount };
    using time_point = std::chrono::system_clock::time_point;
    static std::size_t size() { return Field::Dscount + 1; }
    unsigned long flush_version{};
    time_point start;
    time_point end;
    unsigned long step{};
    unsigned long dscount{};
};

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
