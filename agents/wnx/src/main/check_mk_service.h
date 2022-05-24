// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// check_mk_service.h : The file contains ONLY 'main' function and "root
// supplies"
//
#pragma once
#ifndef check_mk_service_h__
#define check_mk_service_h__
#include <string_view>

namespace cma::cmdline {
// Command Line parameters for service

constexpr int kParamShift = 10;

constexpr std::string_view kUpdaterParam = "updater";  // run cmk_update_plugin
constexpr std::string_view kCmkUpdaterParam = "cmk_update_agent";  // -/-/-/-/-

constexpr std::string_view kRestoreParam = "restore";

constexpr std::string_view kInstallParam = "install";
constexpr std::string_view kRemoveParam = "remove";
constexpr std::string_view kLegacyTestParam = "test";

constexpr std::string_view kCheckParam = "check";
constexpr std::string_view kCheckParamSelf = "-self";
constexpr std::string_view kCheckParamMt = "-mt";
constexpr std::string_view kCheckParamIo = "-io";

constexpr std::string_view kRealtimeParam = "rt";
constexpr std::string_view kHelpParam = "help";
constexpr std::string_view kVersionParam = "version";
constexpr std::string_view kReloadConfigParam = "reload_config";
constexpr std::string_view kRemoveLegacyParam = "remove_legacy";

constexpr std::string_view kUninstallAlert = "uninstall_alert";  // from the msi

constexpr std::string_view kExecParam = "exec";             // runs as app
constexpr std::string_view kAdhocParam = "adhoc";           // runs as app
constexpr std::string_view kExecParamShowWarn = "-show";    // logging sub param
constexpr std::string_view kExecParamShowAll = "-showall";  // logging sub param
constexpr std::string_view kExecParamIntegration = "-integration";  // internal

constexpr std::string_view kCvtParam = "convert";    // convert ini to yaml
constexpr std::string_view kCvtParamShow = "-show";  // logging sub param
constexpr std::string_view kSkypeParam = "skype";    // hidden
constexpr std::string_view kPatchHashParam = "patch_hash";      // hidden
constexpr std::string_view kStopLegacyParam = "stop_legacy";    //
constexpr std::string_view kStartLegacyParam = "start_legacy";  //

constexpr std::string_view kUpgradeParam = "upgrade";      // upgrade LWA
constexpr std::string_view kUpgradeParamForce = "-force";  // upgrade LWA always

constexpr std::string_view kCapParam = "cap";            // install files
constexpr std::string_view kSectionParam = "section";    // dump section
constexpr std::string_view kSectionParamShow = "-show";  // logging sub param

constexpr std::string_view kCapExtractParam = "cap_ex";  // extract all from cap

constexpr std::string_view kShowConfigParam = "showconfig";  // show config

// FIREWALL:
constexpr std::string_view kFwParam = "fw";  // firewall settings
constexpr std::string_view kFwConfigureParam =
    "-configure";                                     // config fw for exe
constexpr std::string_view kFwClearParam = "-clear";  // remove firewall rule

constexpr std::string_view kResetOhm = "resetohm";  // reset ohm as treasury

// Service name and Targeting
#if defined(CMK_SERVICE_NAME)
constexpr const char *const kServiceExeName = "check_mk_agent.exe";
#elif defined(CMK_TEST)
constexpr const char *const kServiceExeName = L"test";
#else
#error "Target not defined properly"
#endif

}  // namespace cma::cmdline
namespace cma {
// we want to test main function too.
int MainFunction(int argc, wchar_t const *argv[]);
}  // namespace cma
#endif  // check_mk_service_h__
