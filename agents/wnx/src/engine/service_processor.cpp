
#include "stdafx.h"

#include "service_processor.h"

#include <fcntl.h>
#include <io.h>
#include <sensapi.h>
#include <shlobj_core.h>

#include <chrono>
#include <cstdint>  // wchar_t when compiler options set weird
#include <ranges>

#include "agent_controller.h"
#include "commander.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "common/wtools_service.h"
#include "common/yaml.h"
#include "external_port.h"
#include "firewall.h"
#include "install_api.h"
#include "providers/perf_counters_cl.h"
#include "realtime.h"
#include "tools/_process.h"
#include "upgrade.h"
#include "windows_service_api.h"

using namespace std::chrono_literals;
using namespace std::string_literals;
namespace fs = std::filesystem;

namespace cma::srv {
extern bool
    g_global_stop_signaled;  // semi-hidden global variable for global status

// Implementation of the Windows signals

void ServiceProcessor::startService() {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return;
    }

    // service must reload config, because service may reconfigure itself
    ReloadConfig();

    rm_lwa_thread_ = std::thread(&cfg::rm_lwa::Execute);

    thread_ = std::thread(&ServiceProcessor::mainThread, this, &external_port_);

    XLOG::l.t("Successful start of thread");
}

void ServiceProcessor::startServiceAsLegacyTest() {
    if (thread_.joinable()) {
        xlog::l("Attempt to start service twice, no way!").print();
        return;
    }
    thread_ = std::thread(&ServiceProcessor::mainThread, this, nullptr);
    thread_.join();
    XLOG::t("Successful legacy start of thread");
}

namespace {
void KillProcessesInUserFolder() {
    std::filesystem::path user_dir{cfg::GetUserDir()};
    std::error_code ec;
    if (user_dir.empty() ||
        std::filesystem::exists(user_dir / cfg::dirs::kUserPlugins, ec)) {
        auto killed_processes_count = wtools::KillProcessesByDir(user_dir);
        XLOG::d.i("Killed [{}] processes from the user folder",
                  killed_processes_count);
    } else {
        XLOG::l("Kill isn't possible, the path '{}' looks as bad", user_dir);
    }
}

void TryCleanOnExit(cfg::modules::ModuleCommander &mc) {
    namespace details = cfg::details;

    KillProcessesInUserFolder();

    if (!g_uninstall_alert.isSet()) {
        XLOG::l.i("Clean on exit was not requested, not uninstall sequence");

        return;
    }

    fw::RemoveRule(srv::kSrvFirewallRuleName);

    auto mode = details::GetCleanDataFolderMode();  // read config
    XLOG::l.i(
        "Clean on exit was requested, trying to remove what we have, mode is [{}]",
        static_cast<int>(mode));
    if (mode != details::CleanMode::none) {
        cfg::modules::ModuleCommander::moveModulesToStore(cfg::GetUserDir());
    }
    details::CleanDataFolder(mode);  // normal
}
}  // namespace

void ServiceProcessor::stopService() {
    XLOG::l.i("Stop Service called");
    srv::g_global_stop_signaled = true;
    {
        std::lock_guard lk(lock_stopper_);
        stop_requested_ = true;  // against spurious wake up
        stop_thread_.notify_one();
    }

    // #TODO (sk): use std::array<std::reference_wrapper<std::thread>, 3> t{};
    if (thread_.joinable()) thread_.join();
    if (process_thread_.joinable()) thread_.join();
    if (rm_lwa_thread_.joinable()) rm_lwa_thread_.join();
}

void ServiceProcessor::cleanupOnStop() {
    XLOG::l.i("Cleanup called by service");

    if (!IsService()) {
        XLOG::l("Invalid call!");
    }
    KillAllInternalUsers();

    TryCleanOnExit(mc_);
}

// #TODO - implement
// this is not so simple we have to pause main IO thread
// and I do not know what todo with external port
void ServiceProcessor::pauseService() { XLOG::l.t("PAUSE is not implemented"); }

// #TODO - implement
void ServiceProcessor::continueService() {
    XLOG::l.t("CONTINUE is not implemented");
}

void ServiceProcessor::shutdownService() { stopService(); }

void ServiceProcessor::stopTestingMainThread() {
    XLOG::t(XLOG_FUNC + " called");
    if (!thread_.joinable()) {
        return;
    }

    {
        std::lock_guard lk(lock_stopper_);
        stop_requested_ = true;
        stop_thread_.notify_one();
    }
    thread_.join();
}

namespace {
std::string FindWinPerfExe() {
    auto exe_name = cfg::groups::winperf.exe();

    if (tools::IsEqual(exe_name, "agent")) {
        XLOG::t.i("Looking for default agent");
        namespace fs = std::filesystem;
        const fs::path f{cfg::GetRootDir()};
        std::vector<fs::path> names{
            f / cfg::kDefaultAppFileName  // on install
        };

        if (tgt::Is64bit()) {
            names.emplace_back(f / "check_mk_service64.exe");
        }

        names.emplace_back(f / "check_mk_service32.exe");

        exe_name.clear();
        for (const auto &name : names) {
            std::error_code ec;
            if (fs::exists(name, ec)) {
                exe_name = name.u8string();
                XLOG::d.i("Using file '{}' for winperf", exe_name);
                break;
            }
        }
        if (exe_name.empty()) {
            XLOG::l.crit("In folder '{}' not found binaries to exec winperf");
            return {};
        }
    } else {
        XLOG::d.i("Looking for agent '{}'", exe_name);
    }
    return exe_name;
}

std::wstring GetWinPerfLogFile() {
    return cfg::groups::winperf.isTrace()
               ? (std::filesystem::path{cfg::GetLogDir()} / "winperf.log")
                     .wstring()
               : L"";
}
}  // namespace

void ServiceProcessor::kickWinPerf(AnswerId answer_id,
                                   const std::string &ip_addr) {
    using cfg::groups::winperf;

    auto cmd_line = winperf.buildCmdLine();
    if (!ip_addr.empty()) {
        // we may need IP info and using for this pseudo-counter
        cmd_line = L"ip:" + wtools::ConvertToUTF16(ip_addr) + L" " + cmd_line;
    }

    auto exe_name = wtools::ConvertToUTF16(FindWinPerfExe());
    auto timeout = winperf.timeout();
    auto prefix = wtools::ConvertToUTF16(winperf.prefix());

    if (winperf.isFork() && !exe_name.empty()) {
        vf_.emplace_back(kickExe(true,                   // async ???
                                 exe_name,               // perf_counter.exe
                                 answer_id,              // answer id
                                 this,                   // context
                                 prefix,                 // for section
                                 timeout,                // in seconds
                                 cmd_line,               // counters
                                 GetWinPerfLogFile()));  // log file
    } else {
        // NOT TESTED with Automatic tests
        XLOG::d("No forking to get winperf data: may lead to handle leak.");
        vf_.emplace_back(std::async(
            std::launch::async, [prefix, this, answer_id, timeout, cmd_line]() {
                auto cs = tools::SplitString(cmd_line, L" ");
                std::vector<std::wstring_view> counters{cs.begin(), cs.end()};
                return provider::RunPerf(prefix,
                                         wtools::ConvertToUTF16(internal_port_),
                                         AnswerIdToWstring(answer_id), timeout,
                                         std::vector<std::wstring_view>{
                                             cs.begin(), cs.end()}) == 0;
            }));
    }
    answer_.newTimeout(timeout);
}

// usually called from the main entry point after connect came to us
// according to spec, we have to update stop time point and parameters from the
// config file
void ServiceProcessor::informDevice(rt::Device &rt_device,
                                    std::string_view ip_addr) const noexcept {
    if (!rt_device.started()) {
        XLOG::l("RT Device is not started");
        return;
    }

    if (!cfg::groups::global.realtimeEnabled()) {
        XLOG::t("Real time is disabled in config");
        return;
    }

    auto sections = cfg::groups::global.realtimeSections();
    if (sections.empty()) return;

    auto s_view = tools::ToView(sections);

    auto rt_port = cfg::groups::global.realtimePort();
    auto password = cfg::groups::global.realtimePassword();
    auto rt_timeout = cfg::groups::global.realtimeTimeout();

    rt_device.connectFrom(ip_addr, rt_port, s_view, password, rt_timeout);
}

void ServiceProcessor::updateMaxWaitTime(int timeout_seconds) noexcept {
    if (timeout_seconds <= 0) {
        return;
    }

    {
        std::lock_guard lk(max_wait_time_lock_);
        max_wait_time_ = std::max(timeout_seconds, max_wait_time_);
    }

    XLOG::t.i("Max Wait Time for Answer is set to [{}]", max_wait_time_);
}

void ServiceProcessor::checkMaxWaitTime() noexcept {
    if (max_wait_time_ <= 0) {
        max_wait_time_ = cfg::kDefaultAgentMinWait;
        XLOG::t.i("Max Wait Time for Answer set to valid value [{}]",
                  max_wait_time_);
    } else
        XLOG::t.i("Max Wait Time for Answer is [{}]", max_wait_time_);
}

void ServiceProcessor::preStartBinaries() {
    XLOG::d.i("Pre Start actions");

    cfg::SetupPluginEnvironment();
    ohm_started_ = conditionallyStartOhm();

    auto &plugins = plugins_provider_.getEngine();
    plugins.registerOwner(this);
    plugins.preStart();
    plugins.detachedStart();

    auto &local = local_provider_.getEngine();
    local.preStart();
    XLOG::d.i("Pre Start actions ended");
}

void ServiceProcessor::detachedPluginsStart() {
    XLOG::t.i("Detached Start");
    auto &plugins = plugins_provider_.getEngine();
    plugins.detachedStart();
}

void ServiceProcessor::resetOhm() noexcept {
    auto powershell_exe = FindPowershellExe();
    if (powershell_exe.empty()) {
        XLOG::l("NO POWERSHELL!");
        return;
    }

    // terminating all
    wtools::KillProcess(provider::ohm::kExeModuleWide, 1);
    cfg::upgrade::StopWindowsService(provider::ohm::kDriverNameWide);
    cfg::upgrade::WaitForStatus(cfg::upgrade::GetServiceStatusByName,
                                provider::ohm::kDriverNameWide, SERVICE_STOPPED,
                                5000);
    auto cmd_line = powershell_exe;
    cmd_line += L" ";
    cmd_line += std::wstring(provider::ohm::kResetCommand);
    XLOG::l.i("I'm going to execute '{}'", wtools::ToUtf8(cmd_line));

    tools::RunStdCommand(cmd_line, true);
}

bool ServiceProcessor::stopRunningOhmProcess() noexcept {
    if (ohm_process_.running()) {
        XLOG::l.i("Stopping running OHM");
        ohm_process_.stop();
        return true;
    }

    return false;
}

// conditions are: yml + exists(ohm) + elevated
// true on successful start or if OHM is already started
bool ServiceProcessor::conditionallyStartOhm() noexcept {
    auto &ohm_engine = ohm_provider_.getEngine();
    if (!ohm_engine.isAllowedByCurrentConfig()) {
        XLOG::t.i("OHM starting skipped due to config");
        stopRunningOhmProcess();
        return false;
    }

    if (!tools::win::IsElevated()) {
        XLOG::d(
            "Starting OHM in non elevated mode has no sense."
            "Please start it by self or change to the elevated mode");
        return false;
    }

    auto ohm_exe = provider::GetOhmCliPath();
    if (!tools::IsValidRegularFile(ohm_exe)) {
        XLOG::d("OHM file '{}' is not found", ohm_exe);
        stopRunningOhmProcess();
        return false;
    }

    auto error_count = ohm_engine.errorCount();
    if (error_count > cfg::kMaxOhmErrorsBeforeRestart) {
        XLOG::l(
            "Too many errors [{}] on the OHM, stopping, cleaning and starting",
            error_count);
        auto stopped = stopRunningOhmProcess();
        resetOhm();
        ohm_engine.resetError();
        if (!stopped) {
            return true;
        }
    } else {
        if (!ohm_process_.running()) {
            XLOG::l.i("OHM is not running by Agent");
            if (wtools::FindProcess(provider::ohm::kExeModuleWide) != 0) {
                XLOG::l.i("OHM is found: REUSE running OHM");
                return true;
            }
        }
    }
    ohm_process_.start(ohm_exe.wstring());
    return true;
}

// This is relative simple function which kicks to call
// different providers
int ServiceProcessor::startProviders(AnswerId answer_id,
                                     const std::string &ip_addr) {
    vf_.clear();
    max_wait_time_ = 0;

    // call of sensible to CPU-load sections
    auto started_sync =
        tryToDirectCall(wmi_cpuload_provider_, answer_id, ip_addr);

    // sections to be kicked out
    tryToKick(uptime_provider_, answer_id, ip_addr);

    if (cfg::groups::winperf.enabledInConfig() &&
        cfg::groups::global.allowedSection(cfg::vars::kWinPerfPrefixDefault)) {
        kickWinPerf(answer_id, ip_addr);
    }

    tryToKick(df_provider_, answer_id, ip_addr);
    tryToKick(mem_provider_, answer_id, ip_addr);
    tryToKick(services_provider_, answer_id, ip_addr);
    tryToKick(ps_provider_, answer_id, ip_addr);
    tryToKick(fileinfo_provider_, answer_id, ip_addr);
    tryToKick(logwatch_event_provider_, answer_id, ip_addr);
    tryToKick(plugins_provider_, answer_id, ip_addr);
    tryToKick(local_provider_, answer_id, ip_addr);

    tryToKick(dotnet_clrmemory_provider_, answer_id, ip_addr);
    tryToKick(wmi_webservices_provider_, answer_id, ip_addr);
    tryToKick(msexch_provider_, answer_id, ip_addr);

    tryToKick(mrpe_provider_, answer_id, ip_addr);
    tryToKick(skype_provider_, answer_id, ip_addr);
    tryToKick(spool_provider_, answer_id, ip_addr);
    tryToKick(ohm_provider_, answer_id, ip_addr);

    checkMaxWaitTime();

    return static_cast<int>(vf_.size()) + (started_sync ? 1 : 0);
}

/// \brief To be used, when no real connection, i.e. test
void ServiceProcessor::sendDebugData() {
    XLOG::l.i("Started without IO. Debug mode");

    auto tp = openAnswer("127.0.0.1");
    if (!tp) return;
    auto started = startProviders(tp.value(), "");
    auto block = getAnswer(started);
    block.emplace_back('\0');  // we need this for printf
    _setmode(_fileno(stdout), _O_BINARY);
    auto count = printf("%s", block.data());
    if (count != block.size() - 1) {
        XLOG::l("Binary data at offset [{}]", count);
    }
}

/// \brief called before every answer to execute routine tasks
void ServiceProcessor::prepareAnswer(const std::string &ip_from,
                                     rt::Device &rt_device) {
    auto value = tools::win::GetEnv(env::auto_reload);

    if (cfg::ReloadConfigAutomatically() || tools::IsEqual(value, L"yes"))
        ReloadConfig();  // automatic config reload

    cfg::SetupRemoteHostEnvironment(ip_from);
    ohm_started_ = conditionallyStartOhm();  // start may happen when
                                             // config changed

    detachedPluginsStart();  // cmk agent update
    informDevice(rt_device, ip_from);
}

// main data source function of the agent
ByteVector ServiceProcessor::generateAnswer(const std::string &ip_from) {
    auto tp = openAnswer(ip_from);
    if (tp) {
        XLOG::d.i("Id is [{}] for ip [{}]", AnswerIdToNumber(tp.value()), ip_from);
        auto count_of_started = startProviders(tp.value(), ip_from);

        return getAnswer(count_of_started);
    }

    XLOG::l.crit("Can't open Answer");
    return makeTestString("No Answer");
}

bool ServiceProcessor::restartBinariesIfCfgChanged(uint64_t &last_cfg_id) {
    // this may race condition, still probability is zero
    // Config Reload is for manual usage
    auto new_cfg_id = cfg::GetCfg().uniqId();
    if (last_cfg_id == new_cfg_id) {
        return false;
    }

    XLOG::l.i("NEW CONFIG with id [{}] prestart binaries", new_cfg_id);
    last_cfg_id = new_cfg_id;
    preStartBinaries();
    return true;
}

// returns break type(what todo)
ServiceProcessor::Signal ServiceProcessor::mainWaitLoop() {
    XLOG::l.i("main Wait Loop");
    // memorize vars to check for changes in loop below
    auto ipv6 = cfg::groups::global.ipv6();
    auto port = cfg::groups::global.port();
    auto uniq_cfg_id = cfg::GetCfg().uniqId();
    ProcessServiceConfiguration(kServiceName);

    // Perform main service function here...
    while (true) {
        if (!callback_(static_cast<const void *>(this))) {
            break;  // special case when thread is one time run
        }

        if (delay_ == 0ms) {
            break;
        }

        // check for config update and inform external port
        auto new_ipv6 = cfg::groups::global.ipv6();
        auto new_port = cfg::groups::global.port();
        if (new_ipv6 != ipv6 || new_port != port) {
            XLOG::l.i("Restarting server with new parameters [{}] ipv6:[{}]",
                      new_port, new_port);
            return Signal::restart;
        }

        // wait and check
        if (timedWaitForStop()) {
            XLOG::l.t("Stop request is set");
            break;  // signaled stop
        }

        if (SERVICE_DISABLED ==
            wtools::WinService::ReadUint32(srv::kServiceName,
                                           wtools::WinService::kRegStart)) {
            XLOG::l("Service is disabled in config, leaving...");

            tools::RunDetachedCommand("net stop "s +
                                      wtools::ToUtf8(kServiceName));
            break;
        }

        restartBinariesIfCfgChanged(uniq_cfg_id);
    }
    XLOG::l.t("main Wait Loop END");
    return Signal::quit;
}

namespace {

void WaitForNetwork(std::chrono::seconds period) {
    using namespace std::chrono_literals;
    constexpr std::chrono::seconds delay = 2s;

    DWORD networks = NETWORK_ALIVE_LAN | NETWORK_ALIVE_WAN;
    for (std::chrono::seconds elapsed = 0s; elapsed < period;) {
        auto ret = ::IsNetworkAlive(&networks);
        auto error = ::GetLastError();
        if (error == 0 && ret == TRUE) {
            XLOG::l.i("The network is available");
            break;
        }

        XLOG::l.i("Check network failed [{}] {}", error, ret);
        std::this_thread::sleep_for(delay);
        elapsed += delay;
    }
}

///  returns non empty port if controller had been started
std::optional<uint16_t> OptionallyStartAgentController(
    std::chrono::milliseconds validate_process_delay) {
    if (!ac ::IsRunController(cfg::GetLoadedConfig())) {
        return {};
    }

    if (auto pid = ac::StartAgentController(wtools::GetArgv(0))) {
        std::this_thread::sleep_for(validate_process_delay);
        if (wtools::GetProcessPath(*pid).empty()) {
            XLOG::l("Controller process pid={} died in {}ms", *pid,
                    validate_process_delay.count());
            ac::DeleteControllerInBin(wtools::GetArgv(0));
            return {};
        }
        return ac::windows_internal_port;
    }

    return {};
}

void OpenFirewall(bool controller) {
    auto rule_name =
        IsService() ? srv::kSrvFirewallRuleName : srv::kAppFirewallRuleName;
    if (controller) {
        XLOG::l.i("Controller has started: firewall to controller");
        ProcessFirewallConfiguration(ac::GetWorkController().wstring(),
                                     GetFirewallPort(), rule_name);
    } else {
        XLOG::l.i("Controller has NOT started: firewall to agent");
        ProcessFirewallConfiguration(wtools::GetArgv(0), GetFirewallPort(),
                                     rule_name);
    }
}

}  // namespace

/// \brief <HOSTING THREAD>
/// ex_port may be nullptr(command line test, for example)
/// makes a mail slot + starts IO on TCP
/// Periodically checks if the service is stopping.
void ServiceProcessor::mainThread(world::ExternalPort *ex_port) noexcept {
    if (IsService()) {
        auto wait_period =
            cfg::GetVal(cfg::groups::kSystem, cfg::vars::kWaitNetwork,
                        cfg::defaults::kServiceWaitNetwork);
        WaitForNetwork(std::chrono::seconds{wait_period});
    }

    ac::CreateLegacyModeFile();
    auto port = OptionallyStartAgentController(1000ms);
    ON_OUT_OF_SCOPE(ac::KillAgentController(wtools::GetArgv(0)));
    OpenFirewall(port.has_value());
    uint16_t use_port = port ? *port
                             : cfg::GetVal(cfg::groups::kGlobal,
                                           cfg::vars::kPort, cfg::kMainPort);

    MailSlot mailbox(
        IsService() ? cfg::kServiceMailSlot : cfg::kTestingMailSlot, 0);
    internal_port_ = carrier::BuildPortName(carrier::kCarrierMailslotName,
                                            mailbox.GetName());
    try {
        mailbox.ConstructThread(SystemMailboxCallback, 20, this,
                                IsService() ? wtools::SecurityLevel::admin
                                            : wtools::SecurityLevel::standard);
        ON_OUT_OF_SCOPE(mailbox.DismantleThread());

        if (IsService()) {
            mc_.InstallDefault(cfg::modules::InstallMode::normal);
            install::ClearPostInstallFlag();
        } else {
            mc_.LoadDefault();
        }

        preStartBinaries();

        WaitForAsyncPluginThreads(5000ms);
        if (ex_port == nullptr) {
            sendDebugData();
            return;
        }

        rt::Device rt_device;

        // Main Processing Loop
        while (true) {
            rt_device.start();
            auto io_started = ex_port->startIo(
                [this, &rt_device](
                    const std::string &ip_addr) -> std::vector<uint8_t> {
                    //
                    // most important entry point for external port io
                    // this is internal implementation of the io_context
                    // called upon kicking in port, i.e. LATER. NOT NOW.
                    //
                    prepareAnswer(ip_addr, rt_device);
                    XLOG::d.i("Generating answer with id [{}]",
                              answer_.getId().time_since_epoch().count());
                    return generateAnswer(ip_addr);
                },
                use_port);
            ON_OUT_OF_SCOPE({
                ex_port->shutdownIo();
                rt_device.stop();
            });

            if (!io_started) {
                XLOG::l.bp("Ups. We cannot start main thread");
                return;
            }

            // we wait her to the end of the External port
            if (mainWaitLoop() == Signal::quit) {
                break;
            }
            XLOG::l.i("restart main loop");
        };

        // the end of the fun
        XLOG::l.i("Thread is stopped");
    } catch (const std::exception &e) {
        XLOG::l.crit("Not expected exception '{}'. Fix it!", e.what());
    } catch (...) {
        XLOG::l.bp("Not expected exception. Fix it!");
    }
    internal_port_ = "";
}

void ServiceProcessor::startTestingMainThread() {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return;
    }

    thread_ = std::thread(&ServiceProcessor::mainThread, this, nullptr);
    XLOG::l.i("Successful start of main thread");
}

// Implementation of the Windows signals
// ---------------- END ----------------

bool SystemMailboxCallback(const MailSlot * /*nothing*/, const void *data,
                           int len, void *context) {
    auto *processor = static_cast<srv::ServiceProcessor *>(context);
    if (processor == nullptr) {
        XLOG::l("error in param");
        return false;
    }

    const auto *dt = static_cast<const carrier::CarrierDataHeader *>(data);
    XLOG::d.i("Received [{}] bytes from '{}'\n", len, dt->providerId());
    switch (dt->type()) {
        case carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            if (dt->data() != nullptr) {
                std::string to_log;
                const auto *data = static_cast<const char *>(dt->data());
                to_log.assign(data, data + dt->length());
                XLOG::l(XLOG::kNoPrefix)("{} : {}", dt->providerId(), to_log);
            } else
                XLOG::l(XLOG::kNoPrefix)("{} : null", dt->providerId());
            break;

        case carrier::DataType::kSegment:
            // IMPORTANT ENTRY POINT
            // Receive data for Section
            {
                std::chrono::nanoseconds duration_since_epoch{dt->answerId()};
                std::chrono::time_point<std::chrono::steady_clock> tp(
                    duration_since_epoch);
                const auto *data_source =
                    static_cast<const uint8_t *>(dt->data());
                const auto *data_end = data_source + dt->length();
                AsyncAnswer::DataBlock vectorized_data(data_source, data_end);

                if (!vectorized_data.empty() && vectorized_data.back() == 0) {
                    XLOG::l("Section '{}' sends null terminated strings",
                            dt->providerId());
                    vectorized_data.pop_back();
                }

                processor->addSectionToAnswer(dt->providerId(), tp,
                                              vectorized_data);
            }
            break;
        case carrier::DataType::kYaml:
            XLOG::l.bp(XLOG_FUNC + " NOT SUPPORTED now");
            break;

        case carrier::DataType::kCommand: {
            auto rcp = commander::ObtainRunCommandProcessor();
            if (rcp != nullptr) {
                std::string cmd(static_cast<const char *>(dt->data()),
                                static_cast<size_t>(dt->length()));
                std::string peer(commander::kMainPeer);

                rcp(peer, cmd);
            }

            break;
        }
    }

    return true;
}

HANDLE CreateDevNull() {
    SECURITY_ATTRIBUTES secattr{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};

    return ::CreateFileA("nul:", GENERIC_READ | GENERIC_WRITE,
                         FILE_SHARE_READ | FILE_SHARE_WRITE, &secattr,
                         OPEN_EXISTING, 0, nullptr);
}

bool TheMiniProcess::start(const std::wstring &exe_name) {
    std::unique_lock lk(lock_);
    if (!wtools::IsInvalidHandle(process_handle_)) {
        // check status and reset handle if required
        DWORD exit_code = STILL_ACTIVE;
        if (::GetExitCodeProcess(process_handle_,
                                 &exit_code) == FALSE ||  // no access
            exit_code != STILL_ACTIVE) {                  // exit?
            if (exit_code != STILL_ACTIVE) {
                XLOG::l.i("Finished with {} code", exit_code);
            }
            ::CloseHandle(process_handle_);
            process_handle_ = wtools::InvalidHandle();
        }
    }

    if (wtools::IsInvalidHandle(process_handle_)) {
        auto *null_handle = CreateDevNull();
        STARTUPINFO si{0};
        si.cb = sizeof(STARTUPINFO);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = null_handle;
        ON_OUT_OF_SCOPE(CloseHandle(null_handle));

        PROCESS_INFORMATION pi{nullptr};
        if (::CreateProcess(exe_name.c_str(), nullptr, nullptr, nullptr, TRUE,
                            0, nullptr, nullptr, &si, &pi) == FALSE) {
            XLOG::l("Failed to run {}", wtools::ToUtf8(exe_name));
            return false;
        }
        process_handle_ = pi.hProcess;
        process_id_ = pi.dwProcessId;
        ::CloseHandle(pi.hThread);  // as in LA

        process_name_ = wtools::ToUtf8(exe_name);
        XLOG::d.i("Started '{}' wih pid [{}]", process_name_, process_id_);
    }

    return true;
}

/// \brief - stops process
/// returns true if killing occurs
bool TheMiniProcess::stop() {
    std::unique_lock lk(lock_);
    if (wtools::IsInvalidHandle(process_handle_)) {
        return false;
    }

    auto name = process_name_;
    auto pid = process_id_;
    auto *handle = process_handle_;

    process_id_ = 0;
    process_name_.clear();
    ::CloseHandle(handle);
    process_handle_ = wtools::InvalidHandle();

    // check status and kill process if required
    DWORD exit_code = STILL_ACTIVE;
    if (::GetExitCodeProcess(handle, &exit_code) == FALSE ||  // no access
        exit_code == STILL_ACTIVE) {                          // running
        lk.unlock();

        // our process either running or we have no access to the
        // process
        // -> try to kill
        if (pid == 0) {
            XLOG::l.bp("Killing 0 process '{}' not allowed", name);
            return false;
        }

        if (wtools::kProcessTreeKillAllowed) {
            wtools::KillProcessTree(pid);
        }

        wtools::KillProcess(pid, 99);
        XLOG::l.t("Killing process [{}] '{}'", pid, name);
        return true;
    }

    XLOG::l.t("Process [{}] '{}' already dead", pid, name);
    return false;
}

}  // namespace cma::srv
