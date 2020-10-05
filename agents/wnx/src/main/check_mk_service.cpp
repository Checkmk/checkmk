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

#include "common/yaml.h"

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
    PrintBlock("Normal Usage:\n", Colors::green, []() {
        return fmt::format(
            "\t{1} <{2}|{3}|{4}|{5}|{6}>\n"
            "\t{2:<{0}} - generates test output\n"
            "\t{3:<{0}} - version of the Agent\n"
            "\t{4:<{0}} - reload configuration files of the Agent\n"
            "\t{5:<{0}} - remove Legacy Agent if installed\n"
            "\t{6:<{0}} - usage\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            // first Row
            kLegacyTestParam, kVersionParam, kReloadConfigParam,
            kRemoveLegacyParam, kHelpParam);
    });
}

void PrintAgentUpdater() {
    using namespace xlog::internal;
    PrintBlock("Agent Updater Usage:\n", Colors::green, []() {
        return fmt::format(
            "\t{1} <{2}|{3}> [args]\n"
            "\t{2}|{3:<{0}} - register Agent using plugins\\cmk_update_agent.checmk.py\n",
            kParamShift,
            kServiceExeName,  // service name from the project definitions
            // first Row
            kUpdaterParam, kCmkUpdaterParam);
    });
}

void PrintSelfCheck() {
    using namespace xlog::internal;
    PrintBlock("Self Checking:\n", Colors::cyan, []() {
        return fmt::format(
            "\t{1} {2} <{3}|{4}|{5} [number of seconds]>\n"
            "\t{2:<{0}} - check test\n"
            "\t\t{3:<{0}} - main thread test\n"
            "\t\t{4:<{0}} - simple self test of internal and external transport\n"
            "\t\t{5:<{0}} - simulates periodical connection from Check MK Site, for example '{1} {2} {5} 13'\n",
            kParamShift, kServiceExeName, kCheckParam, kCheckParamMt,
            kCheckParamIo, kCheckParamSelf);
    });
}

void PrintAdHoc() {
    using namespace xlog::internal;
    PrintBlock("Ad Hoc Testing:\n", Colors::cyan, []() {
        return fmt::format(
            "\t{1} <{2}> [{3}|{4}]\n"
            "\t{2:{0}} - run as application (adhoc mode)\n"
            "\t\t{3:{0}} - send important messages on stdio\n"
            "\t\t{4:{0}} - send ALL messages on stdio\n",
            kParamShift,  //
            kServiceExeName,
            std::string(kExecParam) + "|" + std::string(kAdhocParam),  //
            kExecParamShowWarn, kExecParamShowAll);
    });
}

// obsolete
void PrintLegacyTesting() {
    using namespace xlog::internal;
    PrintBlock("Classic/Legacy Testing:\n", Colors::cyan, []() {
        return fmt::format(
            "\t{1} {2}\n"
            "\t{2:{0}} - legacy(standard) test\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kLegacyTestParam);
    });
}

void PrintReinstallWATO() {
    using namespace xlog::internal;
    PrintBlock(
        "Restore WATO Configuration(only for experienced users):\n",
        Colors::pink, []() {
            return fmt::format(
                "\t{1} {2}\n"
                "\t{2:{0}} - agent tries to restore configuration created by WATO(bakery)\n",
                kParamShift,
                kServiceExeName,  // service name from th project definitions
                kRestoreParam);
        });
}

void PrintInstallUninstall() {
    using namespace xlog::internal;
    PrintBlock(
        "Install or remove service(only for experienced users):\n",
        Colors::pink, []() {
            return fmt::format(
                "\t{1} <{2}|{3}>\n"
                "\t{2:<{0}} - install as a service, Administrative Rights are required\n"
                "\t{3:<{0}} - remove service, Administrative Rights are required\n",
                kParamShift,
                kServiceExeName,  // service name from th project definitions
                // first Row
                kInstallParam, kRemoveParam);
        });
}

void PrintShowConfig() {
    using namespace xlog::internal;
    PrintBlock(
        "Display Config and Environment Variables:\n", Colors::cyan, []() {
            return fmt::format(
                "\t{1} {2} [section]\n"
                "\t{2:<{0}} - show configuration parameters\n"
                "\tsection - optional parameter like global or ps\n"
                "\t\tExample: {1} {2} fileinfo\n",
                kParamShift,
                kServiceExeName,  // service name from th project definitions
                kShowConfigParam);
        });
}

void PrintRealtimeTesting() {
    using namespace xlog::internal;
    PrintBlock("Realtime Testing:\n", Colors::cyan, []() {
        return fmt::format(
            "\t{1} {2}\n"
            "\t{2:{0}} - test realtime data with all sections and encryption\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kRealtimeParam);
    });
}

void PrintCvt() {
    using namespace xlog::internal;
    PrintBlock(
        "Convert Legacy Agent Ini File into Agent Yml file:\n", Colors::pink,
        []() {
            return fmt::format(
                "\t{0} {1} [{2}] <inifile> [yamlfile]\n"
                "\tinifile - from Legacy Agent\n"
                "\tyamlfile - name of an output file\n"
                "\t{2} - display output\n",
                kServiceExeName,  // service name from th project definitions
                kCvtParam, kCvtParamShow);
        });
}

void PrintLwaActivate() {
    using namespace xlog::internal;

    PrintBlock("Activate/Deactivate Legacy Agent:\n", Colors::pink, []() {
        return fmt::format(
            "\t{1} <{2}|{3}>\n"
            "\t{2:{0}} - stop and deactivate legacy agent\n"
            "\t{3:{0}} - activate and start legacy agent(only for testing)\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kStopLegacyParam, kStartLegacyParam);
    });
}

void PrintFirewall() {
    using namespace xlog::internal;

    PrintBlock("Configure Firewall Rule:\n", Colors::pink, []() {
        return fmt::format(
            "\t{1} [{2}|{3}]\n"
            "\t{2:{0}} - configure firewall\n"
            "\t{3:{0}} - clear firewall configuration\n",
            kParamShift, kFwParam, kFwConfigureParam, kFwClearParam);
    });
}

void PrintUpgrade() {
    using namespace xlog::internal;
    PrintBlock("Upgrade Legacy Agent(migration):\n", Colors::pink, []() {
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
        "Install Bakery Files and plugins.cap in install folder:\n",
        Colors::pink, []() {
            return fmt::format(
                "\t{0} {1}\n",
                kServiceExeName,  // service name from th project definitions
                kCapParam);
        });
}

void PrintSectionTesting() {
    using namespace xlog::internal;

    PrintBlock("Test sections individually:\n", Colors::pink, []() {
        return fmt::format(
            "\t{1} {2} {3} [{4} [{5}]] \n"
            "\t\t{3:{0}} - any section name(df, fileinfo and so on)\n"
            "\t\t{4:{0}} - pause between tests in seconds, count of tests are infinite. 0 - test once\n"
            "\t\t{5:{0}} - log output on the stdio\n"
            "\t\t\t example: '{1} {2} df 5 {5}'\n"
            "\t\t\t test section df infinitely long with pause 5 seconds and log output on stdio\n",
            kParamShift,
            kServiceExeName,  // service name from th project definitions
            kSectionParam, "any_section", "number_of_seconds",
            kSectionParamShow);
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
                                Colors::red);
    }

    try {
        PrintMain();
        PrintAgentUpdater();
        PrintSelfCheck();
        PrintAdHoc();
        PrintRealtimeTesting();
        PrintShowConfig();
        PrintCvt();
        PrintLwaActivate();
        PrintFirewall();
        PrintUpgrade();
        PrintCap();
        PrintSectionTesting();
        PrintInstallUninstall();
        PrintReinstallWATO();
    } catch (const std::exception &e) {
        XLOG::l("Exception is '{}'", e.what());  //
    }

    // undocumented
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

// on check
int CheckMainService(const std::wstring &What, int Interval) {
    using namespace std::chrono;

    auto what = wtools::ConvertToUTF8(What);

    if (what == cma::cmdline::kCheckParamMt) return cma::srv::TestMt();
    if (what == cma::cmdline::kCheckParamIo) return cma::srv::TestIo();
    if (what == cma::cmdline::kCheckParamSelf)
        return cma::srv::TestMainServiceSelf(Interval);

    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::l("Unsupported second parameter '{}'\n\t Allowed {}, {} or {}", what,
            cma::cmdline::kCheckParamIo, cma::cmdline::kCheckParamMt,
            cma::cmdline::kCheckParamSelf);

    return 0;
}

namespace srv {
int RunService(std::wstring_view app_name) {
    // entry from the service engine

    using namespace cma::install;
    using namespace std::chrono;
    using namespace cma::cfg;

    cma::details::G_Service = true;  // we know that we are service

    auto ret = cma::srv::ServiceAsService(app_name, 1000ms, [](const void *) {
        // optional commands listed here
        // ********
        // 1. Auto Update when  MSI file is located by specified address
        // this part of code have to be tested manually
        // scripting is possible but complicated
        auto ret = CheckForUpdateFile(
            kDefaultMsiFileName,     // file we are looking for
            GetUpdateDir(),          // dir where file we're searching
            UpdateType::exec_quiet,  // quiet for production
            UpdateProcess::execute,  // start update when file found
            GetUserInstallDir());    // dir where file to backup

        if (ret)
            XLOG::l.i("Install process was initiated - waiting for restart");

        return true;
    });

    if (ret == 0) ServiceUsage(L"");

    return ret == 0 ? 0 : 1;
}
}  // namespace srv

// #TODO Function is over complicated
// we want to test main function too.
// so we have main, but callable
int MainFunction(int argc, wchar_t const *Argv[]) {
    std::set_terminate([]() {
        //
        XLOG::details::LogWindowsEventCritical(999, "Win Agent is Terminated.");
        XLOG::l.bp("Win Agent is Terminated.");
        abort();
    });

    if (argc == 1) {
        return cma::srv::RunService(Argv[0]);
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
        return cma::srv::RemoveMainService();
    }

    if (param == wtools::ConvertToUTF16(kCheckParam)) {
        std::wstring param = argc > 2 ? Argv[2] : L"";
        auto interval = argc > 3 ? ToInt(Argv[3]) : 0;
        return CheckMainService(param, interval);
    }

    if (param == wtools::ConvertToUTF16(kLegacyTestParam)) {
        return cma::srv::TestLegacy();
    }

    if (param == wtools::ConvertToUTF16(kRestoreParam)) {
        return cma::srv::RestoreWATOConfig();
    }

    if (param == wtools::ConvertToUTF16(kExecParam) ||
        param == wtools::ConvertToUTF16(kAdhocParam)) {
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
    if (param == wtools::ConvertToUTF16(kResetOhm)) {
        return cma::srv::ExecResetOhm();
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

    if (param == wtools::ConvertToUTF16(kVersionParam)) {
        return cma::srv::ExecVersion();
    }

    if (param == wtools::ConvertToUTF16(kUpdaterParam) ||
        param == wtools::ConvertToUTF16(kCmkUpdaterParam)) {
        std::vector<std::wstring> params;
        for (int k = 1; k < argc; k++) {
            params.emplace_back(Argv[k]);
        }

        return cma::srv::ExecCmkUpdateAgent(params);
    }

    if (param == wtools::ConvertToUTF16(kPatchHashParam)) {
        return cma::srv::ExecPatchHash();
    }

    if (param == wtools::ConvertToUTF16(kShowConfigParam)) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        return cma::srv::ExecShowConfig(wtools::ConvertToUTF8(second_param));
    }

    if (param == wtools::ConvertToUTF16(kUpgradeParam)) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        return cma::srv::ExecUpgradeParam(
            second_param == wtools::ConvertToUTF16(kUpgradeParamForce));
    }
    // #TODO make a function
    if (param == wtools::ConvertToUTF16(kCvtParam)) {
        if (argc > 2) {
            auto diag =
                cma::tools::CheckArgvForValue(argc, Argv, 2, kCvtParamShow)
                    ? cma::srv::StdioLog::yes
                    : cma::srv::StdioLog::no;

            auto pos = diag == cma::srv::StdioLog::yes ? 3 : 2;
            if (argc <= pos) {
                ServiceUsage(std::wstring(L"inifile is mandatory to call ") +
                             wtools::ConvertToUTF16(kCvtParam) + L"\n");
                return 2;
            }

            std::wstring ini = argc > pos ? Argv[pos] : L"";
            std::wstring yml = argc > pos + 1 ? Argv[pos + 1] : L"";

            return cma::srv::ExecCvtIniYaml(ini, yml, diag);
        } else {
            ServiceUsage(std::wstring(L"Invalid count of parameters for ") +
                         wtools::ConvertToUTF16(kCvtParam) + L"\n");
            return 2;
        }
    }

    if (param == wtools::ConvertToUTF16(kFwParam)) {
        using namespace cma::srv;
        using namespace cma::tools;
        if (argc <= 2) return ExecFirewall(FwMode::show, Argv[0], {});

        if (CheckArgvForValue(argc, Argv, 2, kFwConfigureParam))
            return ExecFirewall(FwMode::configure, Argv[0],
                                kAppFirewallRuleName);

        if (CheckArgvForValue(argc, Argv, 2, kFwClearParam))
            return ExecFirewall(FwMode::clear, Argv[0], kAppFirewallRuleName);

        ServiceUsage(std::wstring(L"Invalid parameter for ") +
                     wtools::ConvertToUTF16(kFwParam) + L"\n");
        return 2;
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

    if (param == wtools::ConvertToUTF16(kCapExtractParam) && argc > 3) {
        std::wstring file = Argv[2];
        std::wstring to = Argv[3];
        return cma::srv::ExecExtractCap(file, to);
    }

    if (param == wtools::ConvertToUTF16(kReloadConfigParam)) {
        cma::srv::ExecReloadConfig();
        return 0;
    }

    if (param == wtools::ConvertToUTF16(kUninstallAlert)) {
        XLOG::l.i("UNINSTALL ALERT");
        cma::srv::ExecUninstallAlert();
        return 0;
    }

    if (param == wtools::ConvertToUTF16(kRemoveLegacyParam)) {
        cma::srv::ExecRemoveLegacyAgent();
        return 0;
    }

    if (param == wtools::ConvertToUTF16(kHelpParam)) {
        ServiceUsage(L"");
        return 0;
    }

    auto text =
        std::wstring(L"Provided Parameter \"") + param + L"\" is not allowed\n";

    ServiceUsage(text);
    return 13;
}
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const *Argv[]) {
    return cma::MainFunction(argc, Argv);
}
#endif
