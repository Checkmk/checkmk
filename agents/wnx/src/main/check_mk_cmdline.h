//
// check_mk_cmdline.h : Command Line support
// supplies"
//
#pragma once
#ifndef check_mk_cmdline_h__
#define check_mk_cmdline_h__
#include <string_view>
#include <tuple>
namespace cma::cmdline {

constexpr std::wstring_view kHiddenCommandEncrypt = L"hc_encrypt";
constexpr std::wstring_view kHiddenCommandDecryptCpp = L"hc_decrypt_cpp";
constexpr std::wstring_view kHiddenCommandDecryptPython = L"hc_decrypt_python";

std::tuple<bool, int> HiddenCommandProcessor(int argc, const wchar_t **argv);

}  // namespace cma::cmdline
#endif  // check_mk_cmdline_h__
