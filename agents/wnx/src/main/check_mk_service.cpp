//
// check_mk_service.cpp : This file contains ONLY the 'main' function.
//
// Precompiled
#include "pch.h"
// system C
// system C++
#include <filesystem>
#include <iostream>
#include <string>

#include "yaml-cpp/yaml.h"

// Project
#include "common/cmdline_info.h"
#include "install_api.h"
#include "windows_service_api.h"

// Personal
#include "cfg.h"
#include "check_mk_service.h"
#include "cma_core.h"
#include "logger.h"
#include "providers/perf_counters_cl.h"

std::filesystem::path G_ProjectPath = PROJECT_DIR_CMK_SERVICE;

namespace cma::cmdline {

void PrintBlock(std::string_view title, xlog::internal::Colors title_color,
                std::function<std::string()> formatter) {
    xlog::sendStringToStdio(title.data(), title_color);
    auto out = formatter();
    printf(out.data());
}

void PrintMain() {
    using namespace xlog::internal;
    PrintBlock("Normal Usage:\n", Colors::kGreen, []() {
        return fmt::format(
            "\t{1} <{2}|{3}|{4}>\n"
            "\t{2:<{0}} - install as a service, Administrative Rights are required\n"
            "\t{3:<{0}} - remove service, Administrative Rights are required\n"
            "\t{4:<{0}} - usage\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            // first Row
            kInstallParam, kRemoveParam, kHelpParam);
    });
}

void PrintSelfCheck() {
    using namespace xlog::internal;
    PrintBlock("Self Checking:\n", Colors::kCyan, []() {
        return fmt::format(
            "\t{1} <{2} [{3}|{4}|{5}] <seconds>]>\n"
            "\t{2:<{0}} - check test\n"
            "\t\t{3:<{0}} - main thread test\n"
            "\t\t{4:<{0}} - internal port test \n"
            "\t\t{5:<{0}} - simulates connection after expiring 'seconds' interval\n",
            kParamShift, kServiceExeName, kCheckParam, kCheckParamMt,
            kCheckParamPort, kCheckParamSelf);
    });
}

void PrintAdHoc() {
    using namespace xlog::internal;
    PrintBlock("Ad Hoc Testing:\n", Colors::kCyan, []() {
        return fmt::format(
            "\t{1} <{2} [{3}|{4}]>\n"
            "\t{2:{0}} - run as application (adhoc mode)\n"
            "\t\t{3:{0}} - send important messages on stdio\n"
            "\t\t{4:{0}} - send ALL messages on stdio\n",
            kParamShift,  //
            kServiceExeName,
            std::string(kExecParam) + "|" + std::string(kAdhocParam),  //
            kExecParamShowWarn, kExecParamShowAll);
    });
}

void PrintLegacyTesting() {
    using namespace xlog::internal;
    PrintBlock("Classic/Legacy Testing:\n", Colors::kCyan, []() {
        return fmt::format(
            "\t{1} <{2}>\n"
            "\t{2:{0}} - legacy(standard) test\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kLegacyTestParam);
    });
}

void PrintRealtimeTesting() {
    using namespace xlog::internal;
    PrintBlock("Realtime Testing:\n", Colors::kCyan, []() {
        return fmt::format(
            "\t{1} <{2}>\n"
            "\t{2:{0}} - test realtime data with all sections and encryption\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kRealtimeParam);
    });
}

void PrintCvt() {
    using namespace xlog::internal;
    PrintBlock(
        "To Convert Legacy Agent Ini File into Agent Yml file:\n",
        Colors::kPink, []() {
            return fmt::format(
                "\t{0} <{1}> <inifile> [yamlfile]\n"
                "\tinifile - from Legacy Agent\n"
                "\tyamlfile - name of an output file\n",
                kServiceExeName,  // service name from th project definitions
                kCvtParam);
        });
}

void PrintLwaActivate() {
    using namespace xlog::internal;

    PrintBlock("To Activate/Deactivate Legacy Agent:\n", Colors::kPink, []() {
        return fmt::format(
            "\t{1} <{2}|{3}>\n"
            "\t{2:{0}} - stop and deactivate legacy agent\n"
            "\t{3:{0}} - activate and start legacy agent(only for testing)\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kStopLegacyParam, kStartLegacyParam);
    });
}

void PrintUpgrade() {
    using namespace xlog::internal;
    PrintBlock("To Upgrade Legacy Agent(migration):\n", Colors::kPink, []() {
        return fmt::format(
            "\t{1} {2} [{3}]\n"
            "\t{2:{0}} - upgrading/migration\n"
            "\t\t{3:{0}} - upgrading/migration is forced( file '{2}' is ignored)\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kUpgradeParam, kUpgradeParamForce,
            cma::cfg::files::kUpgradeProtocol);
    });
}

void PrintCap() {
    using namespace xlog::internal;

    PrintBlock(
        "To Install Bakery Files, plugins.cap and check_mk.ini, in install folder:\n",
        Colors::kPink, []() {
            return fmt::format(
                "\t{0} {1}\n",
                kServiceExeName,  // service name from th project definitions
                kCapParam);
        });
}

void PrintSectionTesting() {
    using namespace xlog::internal;

    PrintBlock("To test Sections individually:\n", Colors::kPink, []() {
        return fmt::format(
            "\t{1} {2} <{3}> [{4} [{5}]] \n"
            "\t\t{3:{0}} - any section name(df, fileinfo and so on)\n"
            "\t\t{4:{0}} - pause between tests in seconds, count of tests are infinite. 0 - test once\n"
            "\t\t{5:{0}} - log output on the stdio\n"
            "\t\t\t example '{1} - {2} df 5 {5}'\n"
            "\t\t\t test section df infinitely long with pause 5 seconds and log output on stdio\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kSectionParam, "any section", "number", kSectionParamShow);
    });
}

}  // namespace cma::cmdline

// print short info about usage plus potential comment about error
static void ServiceUsage(std::wstring_view comment) {
    using namespace wtools;
    using namespace cma::cmdline;
    using namespace xlog::internal;
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::DuplicateOnStdio(true);
    if (!comment.empty()) {
        xlog::sendStringToStdio(wtools::ConvertToUTF8(comment).data(),
                                Colors::kRed);
    }

    try {
        cma::cmdline::PrintMain();
        cma::cmdline::PrintSelfCheck();
        cma::cmdline::PrintAdHoc();
        cma::cmdline::PrintLegacyTesting();
        cma::cmdline::PrintRealtimeTesting();
        cma::cmdline::PrintCvt();
        cma::cmdline::PrintLwaActivate();
        cma::cmdline::PrintUpgrade();
        cma::cmdline::PrintCap();
        cma::cmdline::PrintSectionTesting();
    } catch (const std::exception &e) {
        XLOG::l("Exception is '{}'", e.what());  //
    }

    // undocummneted
    // -winnperf ....... command line for runperf
}

namespace cma {
namespace details {
extern bool G_Service;
}

AppType AppDefaultType() {
    return details::G_Service ? AppType::srv : AppType::exe;
}

template <typename T>
auto ToInt(const T W, int Dflt = 0) noexcept {
    try {
        return std::stoi(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToUInt64(const T W, uint64_t Dflt = 0) noexcept {
    try {
        return std::stoull(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToInt64(const T W, int64_t Dflt = 0) noexcept {
    try {
        return std::stoll(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToUint(const T W, uint32_t Dflt = 0) noexcept {
    try {
        return static_cast<uint32_t>(std::stoul(W));
    } catch (const std::exception &) {
        return Dflt;
    }
}

// Command Lines
// -cvt watest/CheckMK/Agent/check_mk.test.ini
//

// #TODO Function is over complicated
// we want to test main function too.
// so we have main, but callable
int MainFunction(int argc, wchar_t const *Argv[]) {
    if (argc == 1) {
        // entry from the service engine

        using namespace cma::install;
        using namespace std::chrono;
        using namespace cma::cfg;

        cma::details::G_Service = true;  // we know that we are service

        return cma::srv::ServiceAsService(1000ms, [](const void *) {
            // optional commands listed here
            // ********
            // 1. Auto Update when  MSI file is located by specified address
            // this part of code have to be tested manually
            // scripting is possible but complicated
            CheckForUpdateFile(
                kDefaultMsiFileName,     // file we are looking for
                GetUpdateDir(),          // dir where file we're searching
                UpdateType::exec_quiet,  // quiet for production
                UpdateProcess::execute,  // start update when file found
                GetUserInstallDir());    // dir where file to backup
            return true;
        });
    }

    std::wstring param(Argv[1]);
    if (param == cma::exe::cmdline::kRunOnceParam) {
        // to test
        // -runonce winperf file:a.txt id:12345 timeout:20 238:processor
        // NO READING FROM CONFIG. This is intentional

        auto [error_val, name, id_val, timeout_val] =
            cma::exe::cmdline::ParseExeCommandLine(argc - 2, Argv + 2);

        if (error_val != 0) {
            XLOG::l("Invalid parameters in command line [{}]", error_val);
            return 1;
        }

        std::wstring prefix = name;
        std::wstring port = Argv[3];
        std::wstring id = id_val;
        std::wstring timeout = timeout_val;
        std::vector<std::wstring_view> counters;
        for (int i = 6; i < argc; i++) {
            if (std::wstring(L"#") == Argv[i]) break;
            counters.push_back(Argv[i]);
        }

        return cma::provider::RunPerf(prefix, id, port, ToInt(timeout, 20),
                                      counters);
    }

    if (0) {
        // this code is enabled only during testing and debugging
        auto path = G_ProjectPath;
        for (;;) {
            auto yml_test_file =
                G_ProjectPath / "data" / "check_mk.example.yml";
            try {
                YAML::Node config = YAML::LoadFile(yml_test_file.u8string());
            } catch (const std::exception &e) {
                XLOG::l(XLOG_FLINE + " exception %s", e.what());
            } catch (...) {
                XLOG::l(XLOG::kBp)(XLOG_FLINE + " exception bad");
            }
        }
    }

    using namespace cma::cmdline;
    cma::OnStartApp();  // path from EXE

    if (param == wtools::ConvertToUTF16(kInstallParam)) {
        return cma::srv::InstallMainService();
    }
    if (param == wtools::ConvertToUTF16(kRemoveParam)) {
        XLOG::l(XLOG::kStdio | XLOG::kInfo)("service to REMOVE");
        return cma::srv::RemoveMainService();
    }

    if (param == wtools::ConvertToUTF16(kCheckParam)) {
        std::wstring param = argc > 2 ? Argv[2] : L"";
        auto interval = argc > 3 ? ToInt(Argv[3]) : 0;
        return cma::srv::TestMainService(param, interval);
    }

    if (param == wtools::ConvertToUTF16(kLegacyTestParam)) {
        return cma::srv::TestMainService(L"legacy", 0);
    }

    if (param == wtools::ConvertToUTF16(kExecParam)) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";

        auto log_on_screen = cma::srv::StdioLog::no;
        if (second_param == wtools::ConvertToUTF16(kExecParamShowAll))
            log_on_screen = cma::srv::StdioLog::extended;
        else if (second_param == wtools::ConvertToUTF16(kExecParamShowWarn))
            log_on_screen = cma::srv::StdioLog::yes;

        return cma::srv::ExecMainService(log_on_screen);
    }
    if (param == wtools::ConvertToUTF16(kRealtimeParam)) {
        return cma::srv::ExecRealtimeTest(true);
    }
    if (param == kSkypeParam) {
        return cma::srv::ExecSkypeTest();
    }
    if (param == wtools::ConvertToUTF16(kStopLegacyParam)) {
        return cma::srv::ExecStopLegacy();
    }
    if (param == wtools::ConvertToUTF16(kStartLegacyParam)) {
        return cma::srv::ExecStartLegacy();
    }
    if (param == wtools::ConvertToUTF16(kCapParam)) {
        return cma::srv::ExecCap();
    }
    if (param == wtools::ConvertToUTF16(kUpgradeParam)) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        return cma::srv::ExecUpgradeParam(
            second_param == wtools::ConvertToUTF16(kUpgradeParamForce));
    }
    if (param == wtools::ConvertToUTF16(kCvtParam) && argc > 2) {
        std::wstring ini = argc > 2 ? Argv[2] : L"";
        std::wstring yml = argc > 3 ? Argv[3] : L"";

        auto diag = cma::tools::CheckArgvForValue(argc, Argv, 4, kCvtParamShow)
                        ? cma::srv::StdioLog::yes
                        : cma::srv::StdioLog::no;
        return cma::srv::ExecCvtIniYaml(ini, yml, diag);
    }
    if (param == wtools::ConvertToUTF16(kSectionParam) && argc > 2) {
        std::wstring section = Argv[2];
        int delay = argc > 3 ? ToInt(Argv[3]) : 0;
        auto diag =
            cma::tools::CheckArgvForValue(argc, Argv, 4, kSectionParamShow)
                ? cma::srv::StdioLog::yes
                : cma::srv::StdioLog::no;
        return cma::srv::ExecSection(section, delay, diag);
    }

    if (param == wtools::ConvertToUTF16(kHelpParam)) {
        ServiceUsage(L"");
        return 0;
    }

    auto text =
        std::wstring(L"Provided Parameter \"") + param + L"\" is not allowed\n";

    ServiceUsage(text);
    return 2;
}
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const *Argv[]) {
    return cma::MainFunction(argc, Argv);
}
#endif
