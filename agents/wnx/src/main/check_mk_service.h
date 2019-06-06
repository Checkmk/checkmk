//
// check_mk_service.h : The file contains ONLY 'main' function and "root
// supplies"
//
#pragma once
#ifndef check_mk_service_h__
#define check_mk_service_h__
#include <cstdint>
namespace cma::cmdline {
// Command Line parameters for service
constexpr const wchar_t* kInstallParam = L"-install";
constexpr const wchar_t* kRemoveParam = L"-remove";
constexpr const wchar_t* kLegacyTestParam = L"test";
constexpr const wchar_t* kTestParam = L"-test";
constexpr const wchar_t* kRealtimeParam = L"-rt";
constexpr const wchar_t* kHelpParam = L"-help";
constexpr const wchar_t* kExecParam = L"exec";                  // runs as app
constexpr const wchar_t* kAdhocParam = L"adhoc";                // runs as app
constexpr const wchar_t* kExecParamExtend = L"-log";            // runs as app
constexpr const wchar_t* kCvtParam = L"-cvt";                   // install cap file
constexpr const wchar_t* kSkypeParam = L"-skype";               // hidden
constexpr const wchar_t* kStopLegacyParam = L"-stop_legacy";    //
constexpr const wchar_t* kStartLegacyParam = L"-start_legacy";  //
constexpr const wchar_t* kUpgradeParam = L"-upgrade";           // upgrade LWA
constexpr const wchar_t* kCapParam = L"-cap";                   // install files
constexpr const wchar_t* kSectionParam = L"-section";           // dump section

// Service name and Targeting
#if defined(CMK_SERVICE_NAME)
constexpr const char* const kServiceExeName = CMK_SERVICE_NAME;
#elif defined(CMK_TEST)
constexpr const char* const kServiceExeName = L"test";
#else
#error "Target not defined properly"
#endif

}  // namespace cma::cmdline
namespace cma {
// we want to test main function too.
int MainFunction(int argc, wchar_t const* Argv[]);
}  // namespace cma
#endif  // check_mk_service_h__
