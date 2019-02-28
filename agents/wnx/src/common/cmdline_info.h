// Command Line Parameters for whole Agent
// Should be include for
// [+] player
// [+] plugins
// wellknown utils etc.

#pragma once
#include <string>
#include <tuple>

#include "tools/_misc.h"

namespace cma {
namespace exe {
namespace cmdline {
// 1st Param
constexpr const wchar_t* kTestParam = L"-test";
constexpr const wchar_t* kLegacyTestParam = L"test";
constexpr const wchar_t* kHelpParam = L"-help";
constexpr const wchar_t* kRunParam = L"-run";          // runs as app
constexpr const wchar_t* kRunOnceParam = L"-runonce";  // runs as app

constexpr const wchar_t* kId = L"id";
constexpr const wchar_t* kTimeout = L"timeout";

constexpr wchar_t kSplitter = L':';

auto ParseExeCommandLine(int argc, wchar_t const* argv[]) {
    using namespace std;
    auto make_error_answer = [](int ErrorCode) -> auto {
        return make_tuple(ErrorCode, std::wstring(), std::wstring(),
                          std::wstring());
    };

    if (argc < 3) {
        xlog::l("Invalid command line").print();
        return make_error_answer(2);
    }
    // NAME
    std::wstring name = argv[0];

    // PORT
    auto [port_type, port_addr] =
        tools::ParseKeyValue(argv[1], exe::cmdline::kSplitter);
    if (port_type.empty()) {
        xlog::l("Port type is empty").print();
        return make_error_answer(3);
    }
    if (port_addr.empty()) {
        xlog::l("Port addr is empty").print();
        return make_error_answer(4);
    }

    // ID
    auto [id_key, id_val] =
        tools::ParseKeyValue(argv[2], exe::cmdline::kSplitter);
    if (id_key != exe::cmdline::kId) {
        xlog::l("IDkey is bad or absent").print();
        return make_error_answer(5);
    }

    if (id_val.empty()) {
        xlog::l("Value of ID is empty").print();
        return make_error_answer(6);
    }

    // TIMEOUT
    auto [timeout_key, timeout_val] =
        tools::ParseKeyValue(argv[3], exe::cmdline::kSplitter);
    if (timeout_key != exe::cmdline::kTimeout) {
        xlog::l("Timeout Key is bad or absent").print();
        return make_error_answer(7);
    }
    if (timeout_val.empty()) {
        xlog::l("Value of Timeout is empty").print();
        return make_error_answer(8);
    }
    return std::make_tuple(0, name, id_val, timeout_val);
}

// 2-nd param
// port for send data

// 3-rd param
// what to execute
}  // namespace cmdline
}  // namespace exe
};  // namespace cma
