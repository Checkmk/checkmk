
// top level API main file for Check MK Providers
// this file is similar to player one, bu

#pragma once
#include <cstdint>
#include <string>

#include "common/cmdline_info.h"
#include "on_start.h"

namespace cma::provider {
constexpr const wchar_t* kProviderName =
    L"Provider";  // unique name of the provider

// FUNCTIONS BELOW ARE IMPLEMENTED IN THE PROVIDER
void ProgramUsage(const std::wstring& Comment);

//  test [parameters]
int MainTest(int argc, wchar_t const* argv[]);

//  run [parameters]
int MainRun(int argc, wchar_t const* argv[]);

//  run something [parameters]
int MainRunOnce(int argc, wchar_t const* argv[]);

// main
int MainFunction(int argc, wchar_t const* argv[]);

// ********************************************************

// sub form main
inline int MainFunctionCore(int argc, wchar_t const* argv[]) {
    using namespace cma::exe::cmdline;
    auto command = std::wstring(argv[1]);

    // First parameter removed - and also removed command line
    // correction:
    argc -= 2;
    argv += 2;

    // no cache updating
    cma::OnStart(cma::AppType::srv);
    ON_OUT_OF_SCOPE(cma::OnExit());

    // check and call:
    if (command == kTestParam) {
        return cma::provider::MainTest(argc, argv);
    } else if (command == kHelpParam) {
        ProgramUsage(L"");
        return 0;
    } else if (command == kRunParam) {
        return cma::provider::MainRun(argc, argv);
    } else if (command == kRunOnceParam) {
        return cma::provider::MainRunOnce(argc, argv);
    }

    return 11;
}

}  // namespace cma::provider
