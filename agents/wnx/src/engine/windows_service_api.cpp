
// provides basic api to start and stop service
#include "stdafx.h"

#include "windows_service_api.h"  // windows api abstracted

#include <shlobj_core.h>

#include <chrono>
#include <cstdint>   // wchar_t when compiler options set weird
#include <iostream>  // test commands
#include <numeric>

#include "cap.h"
#include "cfg.h"
#include "commander.h"
#include "common/version.h"
#include "common/wtools.h"
#include "common/wtools_service.h"
#include "cvt.h"
#include "external_port.h"  // windows api abstracted
#include "firewall.h"
#include "fmt/color.h"
#include "install_api.h"  // install
#include "modules.h"
#include "realtime.h"
#include "service_processor.h"  // cmk service implementation class
#include "tools/_kbd.h"
#include "tools/_process.h"
#include "upgrade.h"

using namespace std::chrono_literals;

// out of namespace
bool g_skype_testing = false;

namespace cma {

namespace srv {
static std::string_view kYouHaveToBeElevatedMessage =
    "You have to be elevated to use this function.\nPlease, run as Administrator\n";
// on -install
// Doesn't create artifacts in program. Changes registry.
int InstallMainService() {
    XLOG::setup::ColoredOutputOnStdio(true);
    xlog::sendStringToStdio("Service to be installed...\n",
                            xlog::internal::Colors::green);
    if (!cma::tools::win::IsElevated()) {
        xlog::sendStringToStdio(kYouHaveToBeElevatedMessage.data(),
                                xlog::internal::Colors::red);
        return 1;
    }

    auto result = wtools::InstallService(
        cma::srv::kServiceName,         // Name of service
        cma::srv::kServiceDisplayName,  // Name to display
        cma::srv::kServiceStartType,    // Service start type
        nullptr,  // cma::srv::kServiceDependencies,  // Dependencies
        nullptr,  // cma::srv::kServiceAccount,       // Service running account
        nullptr   // cma::srv::kServicePassword       // Password of the account
    );
    return result ? 0 : 1;
}

// on -remove
// Doesn't create artifacts in program. Changes registry.
int RemoveMainService() {
    XLOG::setup::ColoredOutputOnStdio(true);
    xlog::sendStringToStdio("Service to be removed...\n",
                            xlog::internal::Colors::green);
    if (!cma::tools::win::IsElevated()) {
        xlog::sendStringToStdio(kYouHaveToBeElevatedMessage.data(),
                                xlog::internal::Colors::red);
        return 1;
    }

    auto result = wtools::UninstallService(cma::srv::kServiceName);
    return result ? 0 : 1;
}

// #POC: to be deleted
static bool execMsi() {
    wchar_t *str = nullptr;
    if (SHGetKnownFolderPath(FOLDERID_System, KF_FLAG_DEFAULT, NULL, &str) !=
        S_OK)
        return false;
    std::wstring exe = str;
    exe += L"\\msiexec.exe";
    auto command = wtools::ToUtf8(exe);
    std::wstring options =
        L" /i \"C:\\z\\m\\check_mk\\agents\\wnx\\build\\install\\Release\\check_mk_service.msi\" "
        L"REINSTALL=ALL REINSTALLMODE=amus "
        L" /quiet";

    // start process
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcess(nullptr,                          // application name
                       (LPWSTR)(exe + options).c_str(),  // Command line options
                       NULL,   // Process handle not inheritable
                       NULL,   // Thread handle not inheritable
                       FALSE,  // Set handle inheritance to FALSE
                       0,      // No creation flags
                       NULL,   // Use parent's environment block
                       NULL,   // Use parent's starting directory
                       &si,    // Pointer to STARTUPINFO structure
                       &pi))   // Pointer to PROCESS_INFORMATION structure
    {
        return false;
    }

    return true;
}

// #POC This is part of poc, testing command which finds an update file and
// execute it
static void CheckForCommand(std::string &Command) {
    Command = "";
    std::error_code ec;
    auto dir = std::filesystem::current_path(ec);
    std::cout << dir.u8string() << ": tick\n";
    try {
        constexpr const char *kUpdateFileCommandDone = "update.command.done";
        std::string done_file_name = kUpdateFileCommandDone;
        std::ifstream done_file(done_file_name.c_str(), std::ios::binary);

        if (done_file.good()) {
            // first stage - deleting file
            done_file.close();
            auto ret = ::DeleteFileA(done_file_name.c_str());
            if (!ret) {
                xlog::l("Cannot Delete File %s with error %d",
                        done_file_name.c_str(), GetLastError());
                return;
            }
        }
        constexpr const char *kUpdateFileCommand = "update.command";
        std::string command_file_name = kUpdateFileCommand;
        std::ifstream command_file(command_file_name.c_str(), std::ios::binary);

        if (!command_file.good()) return;  // nothing todo

        // now is more interesting event
        xlog::l("File %s found, try to exec command", command_file_name.c_str())
            .print();

        command_file.seekg(0, std::ios::end);
        int length = static_cast<int>(command_file.tellg());
        command_file.seekg(0, std::ios::beg);
        if (length > MAX_PATH) {
            // sanity check - too long file will be ignored
            xlog::l("File %s is too big", command_file_name.c_str()).print();
            return;
        }

        // store command & rename file
        char buffer[MAX_PATH * 2];
        command_file.read(buffer, length);
        buffer[length] = 0;
        command_file.close();
        auto ret =
            ::MoveFileA(command_file_name.c_str(), done_file_name.c_str());
        if (ret) {
            Command = buffer;
            xlog::l("To exec %s", Command.c_str());
            execMsi();
            return;
        }

        xlog::l("Cannot Rename File from to %s %s with error %d",
                done_file_name.c_str(), GetLastError());
    } catch (...) {
    }
    return;
}

// on -test self
int TestMainServiceSelf(int Interval) {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    bool stop = false;

    if (Interval < 0) Interval = 0;
    // not a best method to call thread, but this is only for VISUAL testing
    std::thread kick_and_print([&stop, Interval]() {
        auto port = cma::cfg::groups::global.port();

        using namespace asio;

        io_context ios;
        std::string address = "127.0.0.1";

        ip::tcp::endpoint endpoint(ip::make_address(address), port);

        asio::ip::tcp::socket socket(ios);
        std::error_code ec;

        // give some time to start main thread
        // this is testing routine ergo so primitive method is ok
        cma::tools::sleep(1000);

        while (!stop) {
            auto enc = cma::cfg::groups::global.globalEncrypt();
            auto password = enc ? cma::cfg::groups::global.password() : "";
            socket.connect(endpoint, ec);
            if (ec.value() != 0) {
                XLOG::l("Can't connect to {}:{}, waiting for 5 seconds",
                        address, port);

                // method below is not good, still we do not want
                // to over complicate the code just for testing purposes
                for (int i = 0; i < 5; i++) {
                    if (stop) break;
                    cma::tools::sleep(1000);
                }
                if (stop) break;
                continue;
            }
            error_code error;
            std::vector<char> v;
            for (;;) {
                char text[4096];
                auto count = socket.read_some(asio::buffer(text), error);
                if (error.value()) break;
                if (count) {
                    v.insert(v.end(), text, text + count);
                }
            }
            XLOG::l.i("Received {} bytes", v.size());
            if (enc && password[0]) {
                XLOG::l.i("Decrypting {} bytes", v.size());
                // attempt to decode
                cma::encrypt::Commander e(password);
                auto size = v.size();
                v.resize(size + 1024);
                auto [ret, sz] = e.decode(v.data(), size, true);
                XLOG::l.i("Decrypted {} bytes {}", ret, sz);
            }
            socket.close();

            // methods below is not a good still we do not want
            // to over complicate the code just for testing purposes
            for (int i = 0; i < Interval; i++) {
                if (stop) break;
                cma::tools::sleep(1000);
            }
            if (Interval == 0) break;
        }
        XLOG::l.i("Leaving testing thread");
        if (Interval == 0) XLOG::l.i("\n\nPress any key to end program\n\n");
    });

    ExecMainService(StdioLog::no);  // blocking call waiting for keypress
    stop = true;
    if (kick_and_print.joinable()) {
        XLOG::l.i("Waiting for testing thread");
        kick_and_print.join();
        XLOG::l.i("!");
    }

    return 0;
}

int TestIo() {
    using namespace std::chrono;

    // simple test for ExternalPort. will be disabled in production.
    try {
        XLOG::setup::DuplicateOnStdio(true);
        XLOG::setup::ColoredOutputOnStdio(true);
        cma::world::ExternalPort port(nullptr);
        port.startIo(
            [](const std::string) -> std::vector<uint8_t> {
                return std::vector<uint8_t>();
            },
            50555, world::LocalOnly::yes);
        XLOG::l.i("testing 10 seconds");
        std::this_thread::sleep_until(steady_clock::now() + 10000ms);
        port.shutdownIo();  //

    } catch (const std::exception &e) {
        XLOG::l("Exception is not allowed here {}", e.what());
    }
    return 0;
}

int TestMt() {
    using namespace std::chrono;

    // test for main thread. will be disabled in production
    // to find file, read and start update POC.
    try {
        // XLOG::setup::DuplicateOnStdio(true);
        XLOG::setup::ColoredOutputOnStdio(true);
        using namespace std::chrono;
        std::string command = "";
        cma::srv::ServiceProcessor sp(2000ms, [&command](const void *Sp) {
            CheckForCommand(command);
            if (command[0]) {
                cma::tools::RunDetachedCommand(command);
                command = "";
            }
            return true;
        });
        XLOG::SendStringToStdio("Testing...\n\n", XLOG::Colors::green);
        sp.startTestingMainThread();
        XLOG::SendStringToStdio("\nPress any key\n", XLOG::Colors::green);
        cma::tools::GetKeyPress();
        sp.stopTestingMainThread();

    } catch (const std::exception &e) {
        xlog::l("Exception is not allowed here %s", e.what());
    }
    return 0;
}

int TestLegacy() {
    using namespace std::chrono;

    try {
        // test for main thread. will be disabled in production
        // to find file, read and start update POC.
        using namespace std::chrono;
        std::string command = "";
        cma::srv::ServiceProcessor sp(
            2000ms, [&command](const void *Sp) { return true; });
        sp.startServiceAsLegacyTest();
        sp.stopService();
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + "Exception is not allowed here {}", e.what());
    }
    return 0;
}

int RestoreWATOConfig() {
    try {
        using namespace cma::cfg;
        XLOG::setup::ColoredOutputOnStdio(true);
        XLOG::setup::DuplicateOnStdio(true);
        cap::ReInstall();
        modules::ModuleCommander mc;
        mc.InstallDefault(modules::InstallMode::force);
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + "Exception is not allowed here {}", e.what());
    }
    return 0;
}

static void LogFirewallCreate(bool success) {
    if (success)
        XLOG::SendStringToStdio("The firewall has been successfully configured",
                                XLOG::Colors::green);
    else
        XLOG::SendStringToStdio("Failed to configure firewall",
                                XLOG::Colors::red);
}

static void LogFirewallRemove(bool success) {
    if (success)
        XLOG::SendStringToStdio("The firewall configuration have been cleared",
                                XLOG::Colors::green);
    else
        XLOG::SendStringToStdio("Failed to clear firewall configuration",
                                XLOG::Colors::red);
}

static void LogFirewallFindApp(int count) {
    if (count)
        XLOG::SendStringToStdio(
            fmt::format("The firewall has been configured for this exe\n"),
            XLOG::Colors::green);
    else
        XLOG::SendStringToStdio(
            fmt::format("The firewall has NOT been configured for this exe\n"),
            XLOG::Colors::yellow);
}

static void LogFirewallFindService(int count) {
    if (count)
        XLOG::SendStringToStdio(
            "The firewall has been configured for the service\n",
            XLOG::Colors::green);
    else
        XLOG::SendStringToStdio(
            "The firewall has NOT been configured for  the service\n",
            XLOG::Colors::yellow);
}

int ExecFirewall(srv::FwMode fw_mode, std::wstring_view app_name,
                 std::wstring_view name) {
    using namespace cma::fw;
    try {
        XLOG::setup::ColoredOutputOnStdio(true);
        XLOG::setup::DuplicateOnStdio(true);
        switch (fw_mode) {
            case FwMode::configure: {
                // remove all rules with the same name
                while (RemoveRule(name, app_name))
                    ;
                auto success = CreateInboundRule(name, app_name, -1);
                LogFirewallCreate(success);
                return 0;
            }
            case FwMode::clear:
                if (FindRule(name)) {
                    auto success = RemoveRule(name, app_name);
                    // remove all rules with the same name
                    while (RemoveRule(name, app_name))
                        ;
                    LogFirewallRemove(success);
                    return 0;
                }

                XLOG::SendStringToStdio(
                    "The firewall doesn't exists, nothing to remove",
                    XLOG::Colors::yellow);
                return 0;
            case FwMode::show: {
                auto count = CountRules(kAppFirewallRuleName, app_name);
                LogFirewallFindApp(count);

                count = CountRules(kSrvFirewallRuleName, L"");
                LogFirewallFindService(count);
                return 0;
            }
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + "Exception is not allowed here {}", e.what());
    }
    return 0;
}

int ExecExtractCap(std::wstring_view cap_file, std::wstring_view to) {
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::DuplicateOnStdio(true);
    return cma::cfg::cap::ExtractAll(wtools::ToUtf8(cap_file), to);
}

// on -cvt
// may be used as internal API function to convert ini to yaml
// GTESTED internally
int ExecCvtIniYaml(std::filesystem::path ini_file_name,
                   std::filesystem::path yaml_file_name, StdioLog stdio_log) {
    //
    auto flag = stdio_log == StdioLog::no ? 0 : XLOG::kStdio;
    if (stdio_log != StdioLog::no) {
        XLOG::setup::ColoredOutputOnStdio(true);
    }
    namespace fs = std::filesystem;
    fs::path file = ini_file_name;
    std::error_code ec;
    if (!fs::exists(file, ec)) {
        XLOG::l(flag)("File not found '{}'", ini_file_name);
        return 3;
    }
    cma::cfg::cvt::Parser parser_converter;
    parser_converter.prepare();
    if (!parser_converter.readIni(file, false)) {
        XLOG::l(flag)("Failed Load '{}'", fs::absolute(ini_file_name));
        return 2;
    }
    auto yaml = parser_converter.emitYaml();

    try {
        if (yaml_file_name.empty()) {
            std::cout << yaml;
        } else {
            auto file = yaml_file_name;
            std::ofstream ofs(file.u8string());
            ofs << yaml;
            ofs.close();
            XLOG::l.i(flag, "Successfully Converted {} -> {}",
                      fs::absolute(ini_file_name),
                      fs::absolute(yaml_file_name));
        }
    } catch (const std::exception &e) {
        XLOG::l(flag) << "Exception: '" << e.what() << "' in ExecCvtIniYaml"
                      << std::endl;
        return 1;
    }

    return 0;
}

std::vector<std::wstring> SupportedSections{
    wtools::ConvertToUTF16(cma::section::kDfName)};

// on -section
// NOT GTESTED
int ExecSection(const std::wstring &SecName, int RepeatPause,
                StdioLog stdio_log) {
    //
    XLOG::setup::ColoredOutputOnStdio(true);
    if (stdio_log == StdioLog::yes)
        XLOG::setup::EnableTraceLog(false);
    else
        XLOG::setup::EnableTraceLog(true);

    if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(true);

    auto y = cma::cfg::GetLoadedConfig();
    std::vector<std::string> sections;
    sections.emplace_back(wtools::ToUtf8(SecName));
    cma::cfg::PutInternalArray(cma::cfg::groups::kGlobal,
                               cma::cfg::vars::kSectionsEnabled, sections);
    cma::cfg::ProcessKnownConfigGroups();
    cma::cfg::SetupEnvironmentFromGroups();

    while (1) {
        TestLegacy();
        if (RepeatPause <= 0) break;
        cma::tools::sleep(RepeatPause * 1000);
    }

    return 0;
}

// on -exec
// we run entry point as normal process
// this is testing routine probably eliminated from the production build
// THIS ROUTINE DOESN'T USE wtools::ServiceController and Windows Service API
// Just internal to debug logic
int ExecMainService(StdioLog stdio_log) {
    using namespace std::chrono_literals;
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::SendStringToStdio(
        "Adhoc/Exec Mode,"
        "press any key to stop execution\n",
        XLOG::Colors::cyan);
    auto delay = 1000ms;
    auto processor =
        std::make_unique<ServiceProcessor>(delay, [](const void *some_context) {
    // default embedded callback for exec
    // At the moment does nothing
    // optional commands should be placed here
    // ********
#if 0
            using namespace cma::cfg;
            // Auto Update when  MSI file is located by specified address
            CheckForUpdateFile(
                kDefaultMsiFileName,     // file we are looking for
                GetUpdateDir(),          // dir where file we're searching
                UpdateType::exec_quiet,  // quiet for production
                UpdateProcess::execute,  // start update when file found
                GetUserInstallDir());    // dir where file to backup
#endif
            return true;
        });

    processor->startService();

    try {
        // setup output
        if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(true);

        cma::tools::GetKeyPress();  // blocking  wait for key press
    } catch (const std::exception &e) {
        XLOG::l("Exception '{}'", e.what());
    }

    XLOG::l.i("Server is going to stop");
    processor->stopService();

    if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(false);

    return 0;
}

int ExecVersion() {
    XLOG::setup::ColoredOutputOnStdio(true);
    std::string version =
        fmt::format("Check_MK Agent version {}", CMK_WIN_AGENT_VERSION);

    XLOG::SendStringToStdio(version, XLOG::Colors::white);
    return 0;
}

namespace {
// business Logic settings. Requested by Tickets:
constexpr bool g_use_colored_output_for_agent_updater = false;
constexpr bool g_duplicate_updater_output_on_stdio = false;

//
// NOTE: again, business logic... Probably we have to test this in Unit(easy,
// but public)/Integration(difficult but private) Tests.
//
void ModifyStdio(bool yes) {
    if (g_use_colored_output_for_agent_updater)
        XLOG::setup::ColoredOutputOnStdio(yes);
    if (g_duplicate_updater_output_on_stdio) XLOG::setup::DuplicateOnStdio(yes);
}

void ReportNoPluginDir(const std::filesystem::path &dir) {
    XLOG::l.e("Plugins directory '{}' not found", dir);
    XLOG::SendStringToStdio(
        fmt::format("\n\tPlugins directory '{}' not found.\n"
                    "\tWindows agent's installation may be absent or damaged\n",
                    dir),
        XLOG::Colors::white);
}

namespace {
std::wstring JoinParams(const std::vector<std::wstring> &params) {
    return std::accumulate(std::begin(params), std::end(params), std::wstring(),
                           [](const std::wstring &ss, const std::wstring &s) {
                               return ss.empty() ? s : ss + L" " + s;
                           });
}
}  // namespace

void ReportNoUpdaterFile(const std::filesystem::path &f,
                         const std::vector<std::wstring> &params) {
    XLOG::l.w("Agent Updater File '{}' not found", f);
    XLOG::SendStringToStdio(
        fmt::format(
            "\n\tYou must install Agent Updater Python plugin to use the updater with parameters '{}'.\n"
            "\tTo install the plugin you may use the Bakery.\n"
            "\tAnother possibility is copy Agent Updater file manually into the plugins directory\n",
            wtools::ToUtf8(JoinParams(params))),
        XLOG::Colors::white);
}

void ReportNoPythonModule(const std::vector<std::wstring> &params) {
    XLOG::l.e("Python Module is not installed");

    XLOG::SendStringToStdio(
        fmt::format(
            "\n\tYou must install Python Module to use the updater with parameters '{}'.\n"
            "\tTo install Python Module you should use Bakery.\n",
            wtools::ToUtf8(JoinParams(params))),
        XLOG::Colors::white);
}

}  // namespace

// params is a list of valid cmk-agent-updater commands
// update -v for example
int ExecCmkUpdateAgent(const std::vector<std::wstring> &params) {
    namespace fs = std::filesystem;

    ModifyStdio(true);

    fs::path plugins_dir{cma::cfg::GetUserPluginsDir()};
    if (!fs::exists(plugins_dir)) {
        ReportNoPluginDir(plugins_dir);
        return 1;
    }

    auto updater_file = plugins_dir / cma::cfg::files::kAgentUpdaterPython;
    if (!fs::exists(updater_file)) {
        ReportNoUpdaterFile(updater_file, params);
        return 1;
    }

    XLOG::d.i("'{}' will be used for updater", updater_file);

    cma::cfg::modules::ModuleCommander mc;
    mc.LoadDefault();
    auto command_to_run = mc.buildCommandLine(updater_file.u8string());
    if (command_to_run.empty()) {
        ReportNoPythonModule(params);
        return 1;
    }

    for (auto &p : params) command_to_run += L" " + p;

    cma::cfg::SetupPluginEnvironment();

    ModifyStdio(false);
    auto proc_id = cma::tools::RunStdCommand(command_to_run, true);
    ModifyStdio(true);

    if (proc_id > 0) {
        XLOG::l.i("Agent Updater process [{}] started\n", proc_id);
        return 0;
    }

    XLOG::l("Agent Updater process '{}' failed to start\n",
            wtools::ToUtf8(command_to_run));
    return 1;
}

// on -cap
int ExecCap() {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    XLOG::l.i("Installing...");
    cfg::cap::Install();
    XLOG::l.i("End of!");
    return 0;
}

// on -cap
int ExecPatchHash() {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    XLOG::l.i("Patching...");
    cfg::upgrade::PatchOldFilesWithDatHash();
    XLOG::l.i("End of!");
    return 0;
}

int ExecReloadConfig() {
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::SendStringToStdio("Reloading configuration...\n",
                            XLOG::Colors::white);
    cma::MailSlot mailbox_service(cma::cfg::kServiceMailSlot, 0);
    cma::MailSlot mailbox_test(cma::cfg::kTestingMailSlot, 0);

    XLOG::l.i("Asking for reload service");
    cma::carrier::InformByMailSlot(mailbox_service.GetName(),
                                   cma::commander::kReload);

    XLOG::l.i("Asking for reload executable");
    cma::carrier::InformByMailSlot(mailbox_test.GetName(),
                                   cma::commander::kReload);

    XLOG::SendStringToStdio("Done.", XLOG::Colors::white);
    return 0;
}

int ExecUninstallAlert() {
    cma::MailSlot mailbox_service(cma::cfg::kServiceMailSlot, 0);

    cma::carrier::InformByMailSlot(mailbox_service.GetName(),
                                   cma::commander::kUninstallAlert);
    return 0;
}

// only as testing
static bool CreateTheFile(const std::filesystem::path &dir,
                          std::string_view content) {
    try {
        auto protocol_file = dir / "check_mk_agent.log.tmp";
        std::ofstream ofs(protocol_file, std::ios::binary);

        if (ofs) {
            ofs << "Info Log from check mk agent:\n";
            ofs << "  time: '" << cma::cfg::ConstructTimeString() << "'\n";
            if (!content.empty()) {
                ofs << content;
                ofs << "\n";
            }
        }
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception during creatin protocol file {}", e.what());
        return false;
    }
    return true;
}

// returns codes for main
// 0 - no more Legacy Agent
// 1 - legacy agent is here
// 2 - bad uninstall
int ExecRemoveLegacyAgent() {
    using namespace cma::cfg;
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::SendStringToStdio("Removing Legacy Agent...\n", XLOG::Colors::white);
    ON_OUT_OF_SCOPE(XLOG::SendStringToStdio("Done.", XLOG::Colors::white););

    if (upgrade::FindLegacyAgent().empty()) {
        XLOG::SendStringToStdio(
            "Legacy Agent is absent, no need to uninstall\n",
            XLOG::Colors::green);
        return 0;
    }

    XLOG::SendStringToStdio("This operation may be long, please, wait\n",
                            XLOG::Colors::yellow);
    auto result = UninstallProduct(cma::cfg::products::kLegacyAgent);
    if (result) {
        XLOG::SendStringToStdio("Successful execution of the uninstall file\n",
                                XLOG::Colors::green);
        if (!upgrade::FindLegacyAgent().empty()) {
            XLOG::SendStringToStdio(
                "Legacy Agent is not removed, probably you have to have to be in Elevated Mode\n",
                XLOG::Colors::red);
            return 2;
        }
    } else {
        XLOG::SendStringToStdio("Failed Execution of uninstall file\n",
                                XLOG::Colors::red);
    }

    if (upgrade::FindLegacyAgent().empty()) {
        XLOG::SendStringToStdio("Legacy Agent looks as removed\n",
                                XLOG::Colors::cyan);
        return 0;
    }

    return 1;
}

int ExecShowConfig(std::string_view sec) {
    XLOG::setup::ColoredOutputOnStdio(true);
    using namespace cma::cfg;
    const auto yaml = GetLoadedConfig();
    YAML::Node filtered_yaml =
        sec.empty() ? YAML::Clone(yaml) : YAML::Clone(yaml[sec.data()]);
    cma::cfg::RemoveInvalidNodes(filtered_yaml);
    YAML::Emitter emit;
    emit << filtered_yaml;
    XLOG::SendStringToStdio("# Environment Variables:\n", XLOG::Colors::green);
    ProcessPluginEnvironment([](std::string_view name, std::string_view value) {
        XLOG::stdio("# {}=\"{}\"\n", name, value);
    });

    auto files = wtools::ToUtf8(cma::cfg::GetPathOfLoadedConfig());
    auto file_table = cma::tools::SplitString(files, ",");

    XLOG::SendStringToStdio("# Loaded Config Files:\n", XLOG::Colors::green);
    std::string markers[] = {"# system: ", "# bakery: ", "# user  : "};
    int i = 0;
    for (auto f : file_table) {
        XLOG::SendStringToStdio(markers[i++], XLOG::Colors::white);
        if (f.empty())
            XLOG::SendStringToStdio(" [missing]\n");
        else
            XLOG::SendStringToStdio(f + "\n");
    }

    XLOG::setup::ColoredOutputOnStdio(false);
    XLOG::stdio("\n# {}\n{}\n", sec, emit.c_str());

    return 0;
}

// on -start_legacy
int ExecStartLegacy() {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    cfg::upgrade::FindActivateStartLegacyAgent();
    XLOG::l.i("End of!");

    return 0;
}

// on -stop_legacy
int ExecStopLegacy() {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    cfg::upgrade::FindStopDeactivateLegacyAgent();
    XLOG::l.i("End of!");

    return 0;
}

// on -upgrade
int ExecUpgradeParam(bool force_upgrade) {
    using cfg::upgrade::Force;
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    cfg::upgrade::UpgradeLegacy(force_upgrade ? Force::yes : Force::no);
    XLOG::l.i("End of!");

    return 0;
}

// on -skype
// verify that skype business is present
int ExecSkypeTest() {
    g_skype_testing = true;
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false););
    XLOG::l.i("<<<Skype testing>>>");
    cma::provider::SkypeProvider skype;
    auto result = skype.generateContent(cma::section::kUseEmbeddedName, true);
    XLOG::l.i("*******************************************************");
    if (!result.empty())
        XLOG::l.i("{}", result);
    else {
        auto counter_str = wtools::perf::ReadPerfCounterKeyFromRegistry(
            wtools::perf::PerfCounterReg::english);
        auto *data = counter_str.data();
        const auto *end = counter_str.data() + counter_str.size();
        while (true) {
            // get id
            auto *potential_id = wtools::GetMultiSzEntry(data, end);
            if (potential_id == nullptr) {
                break;
            }

            // get name
            auto *potential_name = wtools::GetMultiSzEntry(data, end);
            if (potential_name == nullptr) {
                break;
            }

            // check name
            result += wtools::ToUtf8(potential_id) + ": " +
                      wtools::ToUtf8(potential_name) + "\n";
        }
        XLOG::l.i("{}", result);
    }
    XLOG::l.i("*******************************************************");
    XLOG::l.i("Using Usual Registry Keys:");

    auto skype_counters = cma::provider::internal::GetSkypeCountersVector();
    skype_counters->clear();
    skype_counters->push_back(L"Memory");
    skype_counters->push_back(L"510");
    result = skype.generateContent(cma::section::kUseEmbeddedName, true);

    XLOG::l.i("*******************************************************");
    XLOG::l.i("{}", result);
    XLOG::l.i("*******************************************************");
    //    skype.generateContent();
    XLOG::l.i("<<<Skype testing END>>>");
    return 0;
}

// on -skype
// verify that skype business is present
int ExecResetOhm() {
    g_skype_testing = true;
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::SendStringToStdio("Resetting OHM internally\n", XLOG::Colors::yellow);
    cma::srv::ServiceProcessor sp;
    sp.resetOhm();
    return 0;
}

constexpr static int kRtTestPort = 5555;
constexpr static std::string_view kRtTestPassword = "axecerc";

// Yet Another Test server for the checking output from realtime main thread
// do NOT use in production
class UdpServer {
public:
    UdpServer(asio::io_context &io_context, short port, bool print)
        : socket_(io_context,
                  asio::ip::udp::endpoint(asio::ip::udp::v4(), port))
        , print_(print) {
        do_receive();
    }

    void do_receive() {
        socket_.async_receive_from(
            asio::buffer(data_, max_length), sender_endpoint_,
            [this](std::error_code /*ec*/, std::size_t bytes_recvd) {
                do_processing(bytes_recvd);
                do_receive();  // asio trick to restart receive
            });
    }

private:
    void do_processing(size_t length) {
        if (!print_ || length == 0) return;

        // decoding
        auto [success, len] = crypt_.decode(
            data_ + cma::rt::kDataOffset, length - cma::rt::kDataOffset, true);

        // printing
        if (success) {
            data_[cma::rt::kDataOffset + len] = 0;
            XLOG::l.t("{}",
                      std::string_view(data_ + cma::rt::kDataOffset, length));
        } else {
            XLOG::l("Failed to decrypt data");
        }

        xlog::sendStringToStdio(
            "Press any key to STOP testing Realtime Sections\n",
            xlog::internal::Colors::pink);
    }

    const std::string password_{kRtTestPassword};
    cma::encrypt::Commander crypt_{password_};

    asio::ip::udp::socket socket_;
    asio::ip::udp::endpoint sender_endpoint_;
    enum { max_length = 16000 };
    char data_[max_length];
    bool print_ = false;
};

void RunTestingUdpServer(asio::io_context *io_context, int port_num,
                         bool print) {
    try {
        UdpServer s(*io_context, port_num, print);

        io_context->run();  // blocking call till the context stopped
    } catch (std::exception &e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

// on -rt
// verify that skype business is present
int ExecRealtimeTest(bool print) {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false););
    rt::Device dev;
    asio::io_context context;
    std::thread thread_with_server(RunTestingUdpServer, &context, kRtTestPort,
                                   print);

    dev.start();

    xlog::sendStringToStdio(
        "Press any key to START testing Realtime Sections\n",
        xlog::internal::Colors::green);
    cma::tools::GetKeyPress();  // blocking  wait for key press
    dev.connectFrom("127.0.0.1", kRtTestPort,
                    {"mem", "df", "winperf_processor"}, kRtTestPassword, 30);
    cma::tools::GetKeyPress();  // blocking  wait for key press
    dev.stop();

    context.stop();
    if (thread_with_server.joinable()) thread_with_server.join();
    return 0;
}

namespace {
YAML::Node GetNodeFromSystem(std::string_view node) {
    auto cfg = cfg::GetLoadedConfig();
    auto os = cfg::GetNode(cfg, cfg::groups::kSystem);
    return cfg::GetNode(os, std::string(node));
}

std::pair<bool, int> RemoveRuleWithTimeout(std::wstring_view name,
                                           std::wstring_view raw_app_name,
                                           std::chrono::milliseconds timeout) {
    auto last = std::chrono::steady_clock::now() + timeout;
    int count = 0;
    XLOG::d.i("Removing all '{}' app: '{}'", wtools::ToUtf8(name),
              wtools::ToUtf8(raw_app_name));
    while (fw::RemoveRule(name, raw_app_name)) {
        ++count;
        if (std::chrono::steady_clock::now() > last) {
            return {false, count};
        }
        XLOG::t.i("Removed!");
    }

    return {true, count};
}

}  // namespace

int GetFirewallPort() {
    auto firewall = GetNodeFromSystem(cfg::vars::kFirewall);
    auto port_mode = cfg::GetVal(firewall, cfg::vars::kFirewallPort,
                                 std::string{cfg::values::kFirewallPortAuto});
    if (port_mode == cfg::values::kFirewallPortAuto) {
        return cfg::GetVal(cfg::groups::kGlobal, cfg::vars::kPort,
                           cma::cfg::kMainPort);
    }
    return -1;  // all ports
}

void ProcessFirewallConfiguration(std::wstring_view app_name, int port,
                                  std::wstring_view rule_name) {
    auto firewall = GetNodeFromSystem(cfg::vars::kFirewall);

    auto firewall_mode = cfg::GetVal(firewall, cfg::vars::kFirewallMode,
                                     std::string(cfg::values::kModeNone));
    if (tools::IsEqual(firewall_mode, cfg::values::kModeConfigure)) {
        XLOG::l.i("Firewall mode is set to configure, adding rule...");
        auto [ok, count] = RemoveRuleWithTimeout(rule_name, app_name, 5000ms);
        if (ok) {
            XLOG::l.i("Removed {} old rules.", count);
        } else {
            XLOG::l("Timeout hits! Removed {} old rules.", count);
        }

        auto success = cma::fw::CreateInboundRule(rule_name, app_name, port);

        if (success)
            XLOG::l.i(
                "Firewall rule '{}' had been added successfully for ports [{}]",
                wtools::ToUtf8(rule_name), port);
        return;
    }

    if (cma::tools::IsEqual(firewall_mode, cfg::values::kModeRemove)) {
        XLOG::l.i("Firewall mode is set to clear, removing rule...");
        auto [ok, count] = RemoveRuleWithTimeout(rule_name, app_name, 5000ms);
        if (!ok) {
            XLOG::l("Timeout hits!");
        }
        if (count != 0)
            XLOG::l.i(
                "Firewall rule '{}' had been removed successfully [{}] times",
                wtools::ToUtf8(rule_name), count);
        else
            XLOG::d.i("Firewall rule '{}' is absent, nothing to remove",
                      wtools::ToUtf8(rule_name));
        return;
    }
}

wtools::WinService::StartMode GetServiceStartModeFromCfg(
    std::string_view text) {
    if (tools::IsEqual(text, cfg::values::kStartModeDemand))
        return wtools::WinService::StartMode::stopped;

    if (tools::IsEqual(text, cfg::values::kStartModeDisabled))
        return wtools::WinService::StartMode::disabled;

    if (tools::IsEqual(text, cfg::values::kStartModeAuto))
        return wtools::WinService::StartMode::started;

    if (tools::IsEqual(text, cfg::values::kStartModeDelayed))
        return wtools::WinService::StartMode::delayed;

    return wtools::WinService::StartMode::started;
}

wtools::WinService::ErrorMode GetServiceErrorModeFromCfg(
    std::string_view mode) {
    if (tools::IsEqual(mode, cfg::values::kErrorModeIgnore))
        return wtools::WinService::ErrorMode::ignore;

    if (tools::IsEqual(mode, cfg::values::kErrorModeLog))
        return wtools::WinService::ErrorMode::log;

    return wtools::WinService::ErrorMode::log;
}

// called once on start of the service
// also on reload of the config
bool ProcessServiceConfiguration(std::wstring_view service_name) {
    using namespace cma::cfg;

    wtools::WinService ws(service_name);

    if (!ws.isOpened()) {
        XLOG::l("Cannot open own configuration");
        return false;
    }

    auto service = GetNodeFromSystem(vars::kService);

    auto start_mode =
        GetVal(service, vars::kStartMode, std::string(defaults::kStartMode));
    auto restart_on_crash =
        GetVal(service, vars::kRestartOnCrash, defaults::kRestartOnCrash);
    auto error_mode =
        GetVal(service, vars::kErrorMode, std::string(defaults::kErrorMode));

    XLOG::l.i("Applying config {} restart_on_crash:{} error_mode: {}",
              start_mode, restart_on_crash, error_mode);

    ws.configureError(GetServiceErrorModeFromCfg(error_mode));
    ws.configureRestart(restart_on_crash);
    ws.configureStart(GetServiceStartModeFromCfg(start_mode));

    return true;
}

namespace {
bool IsServiceProcess() {
    auto win_station = ::GetProcessWindowStation();
    if (win_station == nullptr) {
        return false;  // may happen when not enough user rights
    }

    USEROBJECTFLAGS uof = {0};
    auto success = ::GetUserObjectInformation(win_station, UOI_FLAGS, &uof,
                                              sizeof(USEROBJECTFLAGS), nullptr);
    // service should be NON-VISIBLE
    return success && ((uof.dwFlags & WSF_VISIBLE) == 0);
}
}  // namespace

// entry point in service mode
// normally this is "BLOCKING FOR EVER"
// called by Windows Service Manager
// exception free
// returns -1 on failure
int ServiceAsService(
    std::wstring_view app_name, std::chrono::milliseconds delay,
    const std::function<bool(const void *some_context)> &internal_callback) {
    if (!IsServiceProcess()) {
        return 0;
    }

    cma::OnStartApp();
    XLOG::l.i("service to run");
    ON_OUT_OF_SCOPE(cma::OnExit());

    SelfConfigure();

    // infinite loop to protect from exception in future SEH too
    while (true) {
        // we can exit from the service if service set to disabled
        try {
            std::unique_ptr<wtools::BaseServiceProcessor> processor{
                std::make_unique<ServiceProcessor>(delay, internal_callback)};

            wtools::ServiceController service_controller(std::move(processor));
            auto ret = service_controller.registerAndRun(
                srv::kServiceName);  // we will stay here till
                                     // service will be stopped
                                     // itself or from outside
            switch (ret) {
                case wtools::ServiceController::StopType::normal:
                    XLOG::l.i("Service is stopped normally");
                    return 0;
                case wtools::ServiceController::StopType::fail:
                    XLOG::l.i("Service is stopped due to abnormal situation");
                    return -1;
                case wtools::ServiceController::StopType::no_connect:
                    // may happen when service manager is not available
                    return 0;
            }
        } catch (const std::exception &e) {
            XLOG::l.crit("Exception hit {} in ServiceAsService", e.what());
        } catch (...) {
            XLOG::l.crit("Unknown Exception in ServiceAsService");
        }

        // here only on internal crash, i.e post processing
        auto service = GetNodeFromSystem(cfg::vars::kService);
        auto restart_on_crash = cfg::GetVal(service, cfg::vars::kRestartOnCrash,
                                            cfg::defaults::kRestartOnCrash);

        if (!restart_on_crash) {
            XLOG::l("Leaving Loop while restart on crash is false");
            return -1;
        }
    }
    // reachable only on service stop
}

// we are setting service as restartable using more or less suitable
// parameters set returns false if failed call
bool ConfigureServiceAsRestartable(SC_HANDLE handle) {
    SERVICE_FAILURE_ACTIONS service_fail_actions;
    SC_ACTION fail_actions[3];

    fail_actions[0].Type =
        SC_ACTION_RESTART;         // Failure action: Restart Service
    fail_actions[0].Delay = 2000;  // in milliseconds = 2minutes
    fail_actions[1].Type = SC_ACTION_RESTART;
    fail_actions[1].Delay = 2000;
    fail_actions[2].Type = SC_ACTION_RESTART;
    fail_actions[2].Delay = 2000;

    service_fail_actions.dwResetPeriod =
        3600;  // Reset Failures Counter, in Seconds
    service_fail_actions.lpCommand = nullptr;  // on service failure, not used
    service_fail_actions.lpRebootMsg =
        nullptr;  // Message during rebooting computer
                  // due to service failure, not used

    service_fail_actions.cActions = 3;  // Number of failure action to manage
    service_fail_actions.lpsaActions = fail_actions;

    auto result =
        ::ChangeServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS,
                               &service_fail_actions);  // Apply above settings
    if (result == FALSE) {
        XLOG::l("Error [{}] configuring service", ::GetLastError());
        return false;
    }

    return true;
}

// complementary function to GetServiceFailuerActions
void DeleteServiceFailureActions(SERVICE_FAILURE_ACTIONS *actions) {
    if (actions != nullptr) {
        ::LocalFree(actions);
    }
}

// returns allocated data on success
SERVICE_FAILURE_ACTIONS *GetServiceFailureActions(SC_HANDLE handle) {
    SERVICE_FAILURE_ACTIONS *actions = nullptr;

    DWORD bytes_needed = 0;
    DWORD new_buf_size = 0;
    if (::QueryServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS, nullptr,
                              0, &bytes_needed) == FALSE) {
        if (::GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
            return nullptr;
        }

        // allocation
        new_buf_size = bytes_needed;
        actions = reinterpret_cast<SERVICE_FAILURE_ACTIONS *>(
            ::LocalAlloc(LMEM_FIXED, new_buf_size));
    }

    if (::QueryServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS,
                              reinterpret_cast<LPBYTE>(actions), new_buf_size,
                              &bytes_needed) == TRUE)
        return actions;

    // we have to kill our actions data here
    DeleteServiceFailureActions(actions);

    return nullptr;
}

// Service Global Control
bool g_global_stop_signaled = false;

bool IsGlobalStopSignaled() { return g_global_stop_signaled; }

// returns true ALSO on error(to avoid useless attempts to configure
// non-configurable)
bool IsServiceConfigured(SC_HANDLE handle) {
    auto *actions = GetServiceFailureActions(handle);
    ON_OUT_OF_SCOPE(DeleteServiceFailureActions(actions));

    if (actions != nullptr) {
        return actions->cActions != 0;
    }

    XLOG::l("QueryServiceConfig2 failed [{}]", ::GetLastError());
    return true;
}

// handle must be killed with CloseServiceHandle
SC_HANDLE SelfOpen() {
    auto *manager_handle =
        ::OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (nullptr == manager_handle) {
        XLOG::l.crit("Cannot open SC Manager {}", ::GetLastError());
        return nullptr;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(manager_handle));

    auto *handle = ::OpenService(manager_handle, cma::srv::kServiceName,
                                 SERVICE_ALL_ACCESS);
    if (nullptr == handle) {
        XLOG::l.crit("Cannot open Service {}, error =  {}",
                     wtools::ToUtf8(cma::srv::kServiceName), ::GetLastError());
    }

    return handle;
}

void SelfConfigure() {
    auto *handle = SelfOpen();
    ON_OUT_OF_SCOPE(::CloseServiceHandle(handle));
    if (!IsServiceConfigured(handle)) {
        XLOG::l.i("Configure check mk service");
        ConfigureServiceAsRestartable(handle);
    }
}

}  // namespace srv
}  // namespace cma
