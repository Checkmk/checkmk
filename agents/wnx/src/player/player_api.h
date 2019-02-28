// top level API main file

#pragma once
#include <cstdint>
#include <string>

namespace cma::player {
constexpr const wchar_t* kPlayerName =
    L"PluginPlayer";  // unique name of the plugin player

//  test [parameters]
int MainTest(int argc, wchar_t const* argv[]);

//  run [parameters]
int MainRun(int argc, wchar_t const* argv[]);

//  runonce [parameters]
int MainRunOnce(int argc, wchar_t const* argv[]);

// main
int MainFunction(int argc, wchar_t const* argv[]);

}  // namespace cma::player
