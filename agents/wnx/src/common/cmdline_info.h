// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Command Line Parameters for whole Agent
// Should be include for
// [+] player
// [+] plugins
// wellknown utils etc.

#pragma once
#include <string>

#include "tools/_misc.h"

namespace cma {
namespace exe {
namespace cmdline {
// 1st Param
constexpr const wchar_t *kTestParam = L"-test";
constexpr const wchar_t *kLegacyTestParam = L"test";
constexpr const wchar_t *kHelpParam = L"-help";
constexpr const wchar_t *kRunParam = L"-run";          // runs as app
constexpr const wchar_t *kRunOnceParam = L"-runonce";  // runs as app

constexpr const wchar_t *kId = L"id";
constexpr const wchar_t *kTimeout = L"timeout";

constexpr wchar_t kSplitter = L':';

struct ExeCommandLine {
    int error_code;
    std::wstring name;
    std::wstring id_val;
    std::wstring timeout_val;
};

inline ExeCommandLine ParseExeCommandLine(
    const std::vector<std::wstring> &args) {
    auto make_error_answer = [](int error_code) {
        return ExeCommandLine{.error_code = error_code,
                              .name = {},
                              .id_val = {},
                              .timeout_val = {}};
        ;
    };

    if (args.size() < 3) {
        return make_error_answer(2);
    }
    // NAME
    std::wstring name = args[0];

    // PORT
    auto [port_type, port_addr] =
        tools::ParseKeyValue(args[1], exe::cmdline::kSplitter);
    if (port_type.empty()) {
        return make_error_answer(3);
    }
    if (port_addr.empty()) {
        return make_error_answer(4);
    }

    // ID
    auto [id_key, id_val] =
        tools::ParseKeyValue(args[2], exe::cmdline::kSplitter);
    if (id_key != exe::cmdline::kId) {
        return make_error_answer(5);
    }

    if (id_val.empty()) {
        return make_error_answer(6);
    }

    // TIMEOUT
    auto [timeout_key, timeout_val] =
        tools::ParseKeyValue(args[3], exe::cmdline::kSplitter);
    if (timeout_key != exe::cmdline::kTimeout) {
        return make_error_answer(7);
    }
    if (timeout_val.empty()) {
        return make_error_answer(8);
    }

    return ExeCommandLine{.error_code = 0,
                          .name = name,
                          .id_val = id_val,
                          .timeout_val = timeout_val};
}

// 2-nd param
// port for send data

// 3-rd param
// what to execute
}  // namespace cmdline
}  // namespace exe
};  // namespace cma
