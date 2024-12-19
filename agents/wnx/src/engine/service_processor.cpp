
#include "stdafx.h"

#include "wnx/service_processor.h"

#include <fcntl.h>
#include <io.h>
#include <sensapi.h>
#include <shlobj_core.h>

#include <chrono>
#include <cstdint>  // wchar_t when compiler options set weird

#include "common/cma_yml.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "common/wtools_service.h"
#include "common/yaml.h"
#include "providers/perf_counters_cl.h"
#include "tools/_process.h"
#include "wnx/agent_controller.h"
#include "wnx/cap.h"
#include "wnx/cfg_details.h"
#include "wnx/commander.h"
#include "wnx/extensions.h"
#include "wnx/external_port.h"
#include "wnx/firewall.h"
#include "wnx/install_api.h"
#include "wnx/realtime.h"
#include "wnx/upgrade.h"
#include "wnx/windows_service_api.h"

using namespace std::chrono_literals;
using namespace std::string_literals;
namespace fs = std::filesystem;

namespace cma::srv {
enum class FirewallController { with, without };
std::wstring_view RuleName() {
    switch (GetModus()) {
        case Modus::service:
            return srv::kSrvFirewallRuleName;
        case Modus::app:
        case Modus::test:
        case Modus::integration:
            return srv::kAppFirewallRuleName;
    }
    // unreachable
    return {};
}

void OpenFirewall(FirewallController w) {
    const auto rule_name = RuleName();
    switch (w) {
        case FirewallController::with:
            XLOG::l.i("Controller has started: firewall to controller");
            ProcessFirewallConfiguration(ac::GetWorkController().wstring(),
                                         GetFirewallPort(), rule_name);
            break;
        case FirewallController::without:
            XLOG::l.i("Controller has NOT started: firewall to agent");
            ProcessFirewallConfiguration(wtools::GetArgv(0), GetFirewallPort(),
                                         rule_name);
            break;
    }
}

void ServiceProcessor::startService() {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return;
    }

    const auto results = executeOptionalTasks();
    rm_lwa_thread_ = std::thread(&cfg::rm_lwa::Execute);
    thread_ = std::thread(&ServiceProcessor::mainThread, this, &external_port_,
                          results.cap_installed);

    XLOG::l.t("Successful start of thread");
}

ServiceProcessor::OptionalTasksResults
ServiceProcessor::executeOptionalTasks() {
    switch (GetModus()) {
        case Modus::service: {
            const bool installed = cfg::cap::Install();
            cfg::upgrade::UpgradeLegacy(cfg::upgrade::Force::no);
            // service must reload config: service may reconfigure itself
            ReloadConfig();
            return {.cap_installed = installed};
        }
        case Modus::integration:
            [[fallthrough]];
        case Modus::app:
            [[fallthrough]];
        case Modus::test:
            break;
    }
    return {};
}

void ServiceProcessor::startServiceAsLegacyTest() {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return;
    }
    thread_ = std::thread(&ServiceProcessor::mainThreadAsTest, this);
    thread_.join();
    XLOG::t("Successful legacy start of thread");
}

namespace {
void KillProcessesInUserFolder() {
    fs::path user_dir{cfg::GetUserDir()};
    std::error_code ec;
    if (user_dir.empty() ||
        fs::exists(user_dir / cfg::dirs::kUserPlugins, ec)) {
        auto killed_processes_count = wtools::KillProcessesByDir(user_dir);
        XLOG::d.i("Killed [{}] processes from the user folder",
                  killed_processes_count);
    } else {
        XLOG::l("Kill isn't possible, the path '{}' looks as bad", user_dir);
    }
}

void TryCleanOnExit() {
    namespace details = cfg::details;

    KillProcessesInUserFolder();

    if (!g_uninstall_alert.isSet()) {
        XLOG::l.i("Clean on exit was not requested, not uninstall sequence");

        return;
    }

    fw::RemoveRule(srv::kSrvFirewallRuleName);
    install::api_err::Clean();

    const auto mode = details::GetCleanDataFolderMode();  // read config
    XLOG::l.i(
        "Clean on exit was requested, trying to remove what we have, mode is [{}]",
        static_cast<int>(mode));
    if (mode != details::CleanMode::none) {
        cfg::modules::ModuleCommander::moveModulesToStore(cfg::GetUserDir());
    }
    details::CleanDataFolder(mode);  // normal
}
}  // namespace

void ServiceProcessor::stopService(wtools::StopMode stop_mode) {
    XLOG::l.i("Stop Service called");
    if (stop_mode == wtools::StopMode::cancel) {
        srv::CancelAll(true);
    }
    {
        std::lock_guard lk(lock_stopper_);
        stop_requested_ = true;  // against spurious wake up
        stop_thread_.notify_one();
    }

    // #TODO (sk): use std::array<std::reference_wrapper<std::thread>, 3> t{};
    if (thread_.joinable()) {
        thread_.join();
    }
    if (process_thread_.joinable()) {
        thread_.join();
    }
    if (rm_lwa_thread_.joinable()) {
        rm_lwa_thread_.join();
    }
}

void ServiceProcessor::cleanupOnStop() {
    XLOG::l.i("Cleanup called by service");

    if (GetModus() != Modus::service) {
        XLOG::l("Invalid call!");
    }

    TryCleanOnExit();
}

// #TODO - implement
// this is not so simple we have to pause main IO thread
// and I do not know what todo with external port
void ServiceProcessor::pauseService() { XLOG::l.t("PAUSE is not implemented"); }

// #TODO - implement
void ServiceProcessor::continueService() {
    XLOG::l.t("CONTINUE is not implemented");
}

void ServiceProcessor::shutdownService(wtools::StopMode stop_mode) {
    stopService(stop_mode);
}

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

std::string FindWinPerfExe(std::string_view exe_name) {
    if (!tools::IsEqual(exe_name, "agent")) {
        XLOG::d.i("Looking for agent '{}'", exe_name);
        return std::string{exe_name};
    }

    XLOG::t.i("Looking for default agent");
    const fs::path f{cfg::GetRootDir()};
    std::vector names{f / cfg::kDefaultAppFileName};

    if constexpr (tgt::Is64bit()) {
        names.emplace_back(f / "check_mk_service64.exe");
    }

    names.emplace_back(f / "check_mk_service32.exe");

    for (const auto &name : names) {
        std::error_code ec;
        if (fs::exists(name, ec)) {
            XLOG::d.i("Using file '{}' for winperf", name);
            return name.string();
        }
    }

    XLOG::l.crit("In folder '{}' not found binaries to exec winperf");
    return {};
}

namespace {
std::wstring GetWinPerfLogFile() {
    return cfg::groups::g_winperf.isTrace()
               ? (fs::path{cfg::GetLogDir()} / "winperf.log").wstring()
               : L"";
}
}  // namespace

void ServiceProcessor::kickWinPerf(AnswerId answer_id,
                                   const std::string &ip_addr) {
    auto cmd_line = cfg::groups::g_winperf.buildCmdLine();
    if (!ip_addr.empty()) {
        // we may need IP info and using for this pseudo-counter
        cmd_line = L"ip:" + wtools::ConvertToUtf16(ip_addr) + L" " + cmd_line;
    }

    auto exe_name =
        wtools::ConvertToUtf16(FindWinPerfExe(cfg::groups::g_winperf.exe()));
    const auto timeout = cfg::groups::g_winperf.timeout();
    auto prefix = wtools::ConvertToUtf16(cfg::groups::g_winperf.prefix());

    if (cfg::groups::g_winperf.isFork() && !exe_name.empty()) {
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
            std::launch::async, [prefix, this, answer_id, timeout, cmd_line] {
                auto cs = tools::SplitString(cmd_line, L" ");
                std::vector<std::wstring_view> counters{cs.begin(), cs.end()};
                return provider::RunPerf(prefix,
                                         wtools::ConvertToUtf16(internal_port_),
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

    if (!cfg::groups::g_global.realtimeEnabled()) {
        XLOG::t("Real time is disabled in config");
        return;
    }

    auto sections = cfg::groups::g_global.realtimeSections();
    if (sections.empty()) {
        return;
    }

    const std::vector<std::string_view> s_view{sections.begin(),
                                               sections.end()};

    const auto rt_port = cfg::groups::g_global.realtimePort();
    const auto password = cfg::groups::g_global.realtimePassword();
    const auto rt_timeout = cfg::groups::g_global.realtimeTimeout();

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

    tools::RunStdCommand(cmd_line, tools::WaitForEnd::yes);
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
        const auto stopped = stopRunningOhmProcess();
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

namespace {
bool UsePerfCpuLoad(const YAML::Node &config) {
    const auto g = yml::GetNode(config, std::string{cfg::groups::kGlobal});
    return yml::GetVal(g, std::string{cfg::vars::kCpuLoadMethod},
                       std::string{cfg::defaults::kCpuLoad}) ==
           cfg::values::kCpuLoadPerf;
}
}  // namespace

// This is relative simple function which kicks to call
// different providers
int ServiceProcessor::startProviders(AnswerId answer_id,
                                     const std::string &ip_addr) {
    bool use_perf_cpuload = UsePerfCpuLoad(cfg::GetLoadedConfig());
    vf_.clear();
    max_wait_time_ = 0;

    // call of sensible to CPU-load sections
    const auto started_sync =
        use_perf_cpuload
            ? tryToDirectCall(perf_cpuload_provider_, answer_id, ip_addr)
            : tryToDirectCall(wmi_cpuload_provider_, answer_id, ip_addr);

    // sections to be kicked out
    tryToKick(uptime_provider_, answer_id, ip_addr);

    if (cfg::groups::g_winperf.enabledInConfig() &&
        cfg::groups::g_global.allowedSection(
            cfg::vars::kWinPerfPrefixDefault)) {
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
    tryToKick(agent_plugins_, answer_id, ip_addr);

    checkMaxWaitTime();

    return static_cast<int>(vf_.size()) + (started_sync ? 1 : 0);
}

/// To be used, when no real connection, i.e. test
void ServiceProcessor::sendDebugData() {
    XLOG::l.i("Started without IO. Debug mode");

    auto tp = openAnswer("127.0.0.1");
    if (!tp) return;
    auto started = startProviders(tp.value(), "");
    auto block = getAnswer(started);
    block.emplace_back('\0');  // we need this for printf
    _setmode(_fileno(stdout), _O_BINARY);
    auto count = static_cast<size_t>(printf("%s", block.data()));  // NOLINT
    if (count != block.size() - 1) {
        XLOG::l("Binary data at offset [{}]", count);
    }
}

/// called before every answer to execute routine tasks
void ServiceProcessor::prepareAnswer(const std::string &ip_from,
                                     rt::Device &rt_device) {
    const auto value = tools::win::GetEnv(env::auto_reload);

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
        XLOG::d.i("Id is [{}] for ip [{}]", AnswerIdToNumber(tp.value()),
                  ip_from);
        auto count_of_started = startProviders(tp.value(), ip_from);

        return getAnswer(count_of_started);
    }

    XLOG::l.crit("Can't open Answer");
    return makeTestString("No Answer");
}

namespace {
bool FindProcessByPid(uint32_t pid) {
    bool found = false;
    wtools::ScanProcessList([&found, pid](const PROCESSENTRY32 &entry) {
        if (entry.th32ProcessID == pid) {
            found = true;
            return wtools::ScanAction::terminate;
        }
        return wtools::ScanAction::advance;
    });
    return found;
}

}  // namespace

bool ServiceProcessor::restartBinariesIfCfgChanged(uint64_t &last_cfg_id) {
    // this may race condition, still probability is zero
    // Config Reload is for manual usage
    auto new_cfg_id = cfg::details::ConfigInfo::uniqId();
    if (last_cfg_id == new_cfg_id) {
        return false;
    }

    XLOG::l.i("NEW CONFIG with id [{}] prestart binaries", new_cfg_id);
    last_cfg_id = new_cfg_id;
    preStartBinaries();
    return true;
}

// returns break type(what todo)
ServiceProcessor::Signal ServiceProcessor::mainWaitLoop(
    std::optional<ControllerParam> &controller_param) {
    XLOG::l.i("main Wait Loop");
    // memorize vars to check for changes in loop below
    const auto ipv6 = cfg::groups::g_global.ipv6();
    const auto port = cfg::groups::g_global.port();
    auto uniq_cfg_id = cfg::details::ConfigInfo::uniqId();
    if (GetModus() == Modus::service) {
        ProcessServiceConfiguration(kServiceName);
    }

    auto last_check = std::chrono::steady_clock::now();

    // Perform main service function here...
    while (true) {
        if (!callback_()) {
            break;
        }

        if (delay_ == 0ms) {
            break;  // special case when thread is one time run
        }

        // check for config update and inform external port
        auto new_ipv6 = cfg::groups::g_global.ipv6();
        auto new_port = cfg::groups::g_global.port();
        if (new_ipv6 != ipv6 || new_port != port) {
            XLOG::l.i("Restarting server with new parameters [{}] ipv6:[{}]",
                      new_port, new_ipv6);
            return Signal::restart;
        }

        if (controller_param.has_value() &&
            std::chrono::steady_clock::now() - last_check > 30s) {
            if (!FindProcessByPid(controller_param->pid)) {
                XLOG::d("Process of the controller is dead [{}]",
                        controller_param->pid);
                if (ac::IsConfiguredEmergencyOnCrash()) {
                    controller_param.reset();
                    XLOG::d("Restarting");
                    return Signal::restart;
                }
            }
            last_check = std::chrono::steady_clock::now();
        }

        // wait and check
        if (timedWaitForStop()) {
            XLOG::l.t("Stop request is set");
            break;  // signaled stop
        }

        if (SERVICE_DISABLED ==
            wtools::WinService::readUint32(srv::kServiceName,
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

void WaitForNetwork(std::chrono::seconds period) noexcept {
    constexpr auto delay = 2s;

    DWORD networks = NETWORK_ALIVE_LAN | NETWORK_ALIVE_WAN;
    for (auto elapsed = 0s; elapsed < period;) {
        auto ret = ::IsNetworkAlive(&networks);
        auto error = ::GetLastError();
        if (error == 0 && ret == TRUE) {
            XLOG::l.i("The network is available");
            break;
        }

        XLOG::l.i("Check network failed [{}] {}", error, ret);
        try {
            std::this_thread::sleep_for(delay);
        } catch (const std::exception & /*e*/) {
        }
        elapsed += delay;
    }
}

///  returns non empty port if controller had been started
std::optional<ServiceProcessor::ControllerParam> OptionallyStartAgentController(
    std::chrono::milliseconds validate_process_delay) {
    if (ac ::IsRunController(cfg::GetLoadedConfig())) {
        if (const auto pid = ac::StartAgentController()) {
            std::this_thread::sleep_for(validate_process_delay);
            if (!wtools::GetProcessPath(*pid).empty()) {
                OpenFirewall(FirewallController::with);
                return ServiceProcessor::ControllerParam{
                    .port = ac::GetConfiguredAgentChannelPort(GetModus()),
                    .pid = *pid,
                };
            }
            XLOG::l("Controller process pid={} died in {}ms", *pid,
                    validate_process_delay.count());
            ac::DeleteControllerInBin();
        }
    }
    OpenFirewall(FirewallController::without);
    return {};
}

world::ExternalPort::IoParam AsIoParam(
    const std::optional<srv::ServiceProcessor::ControllerParam> &cp) {
    const auto port = cp.has_value()
                          ? cp->port
                          : cfg::GetVal(cfg::groups::kGlobal, cfg::vars::kPort,
                                        cfg::kMainPort);
    return {
        .port = port,
        .local_only = cp.has_value() && ac::GetConfiguredLocalOnly()
                          ? world::LocalOnly::yes
                          : world::LocalOnly::no,
        .pid = cp.has_value() && (ac::GetConfiguredCheck() || port == 0U)
                   ? cp->pid
                   : std::optional<uint32_t>{},
    };
}

void PrepareTempFolder() {
    try {
        const auto path = wtools::MakeSafeTempFolder(wtools::safe_temp_sub_dir);
        if (path.has_value()) {
            for (const auto &entry :
                 std::filesystem::directory_iterator(*path)) {
                fs::remove_all(entry.path());
            }
            XLOG::l.i("Temp folder: {}", path);
        } else {
            XLOG::l("Failed to create temp folder");
        }

    } catch (const std::exception &e) {
        XLOG::l("Failed to create temp folder: {}", e.what());
    }
}
}  // namespace

/// <HOSTING THREAD>
/// ex_port may be nullptr(command line test, for example)
/// cap_installed is signaled from the service thread about cap_installation
/// makes a mail slot + starts IO on TCP
/// Periodically checks if the service is stopping.
void ServiceProcessor::mainThread(world::ExternalPort *ex_port,
                                  bool cap_installed) noexcept {
    const auto is_service = GetModus() == Modus::service;
    if (is_service) {
        auto wait_period =
            cfg::GetVal(cfg::groups::kSystem, cfg::vars::kWaitNetwork,
                        cfg::defaults::kServiceWaitNetwork);
        WaitForNetwork(std::chrono::seconds{wait_period});
    }

    try {
        mailslot::Slot mailbox(GetModus(), ::GetCurrentProcessId());
        internal_port_ = carrier::BuildPortName(carrier::kCarrierMailslotName,
                                                mailbox.GetName());
        mailbox.ConstructThread(SystemMailboxCallback, 20, this,
                                is_service ? wtools::SecurityLevel::admin
                                           : wtools::SecurityLevel::standard);
        ON_OUT_OF_SCOPE(mailbox.DismantleThread());

        auto controller_params = OptionallyStartAgentController(1000ms);

        ON_OUT_OF_SCOPE(ac::KillAgentController());
        if (cap_installed) {
            ac::CreateArtifacts(fs::path{tools::win::GetSomeSystemFolder(
                                    FOLDERID_ProgramData)} /
                                    ac::kCmkAgentUninstall,
                                controller_params.has_value());
        }
        if (is_service) {
            mc_.InstallDefault(cfg::modules::InstallMode::normal);
            install::ClearPostInstallFlag();
            PrepareTempFolder();
        } else {
            mc_.LoadDefault();
        }

        auto to_load = is_service
                           ? cfg::extensions::GetAll(cfg::GetLoadedConfig())
                           : std::vector<cfg::extensions::Extension>{};
        cfg::extensions::ExtensionsManager em{
            to_load, cfg::vars::kExtensionDefaultCheckPeriod};

        preStartBinaries();

        WaitForAsyncPluginThreads(5000ms);
        if (ex_port == nullptr) {
            sendDebugData();
            return;
        }

        // Main Processing Loop
        bool run = true;
        while (run) {
            rt::Device rt_device;
            rt_device.start();
            const auto io_param = AsIoParam(controller_params);
            XLOG::l.i("Starting io with {} {}", io_param.port, io_param.pid);
            auto io_started = ex_port->startIo(
                [this, &rt_device](const std::string &ip_addr) {
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
                io_param);
            ON_OUT_OF_SCOPE({
                ex_port->shutdownIo();
                rt_device.stop();
            });

            if (!io_started) {
                XLOG::l.bp("Ups. We cannot start main thread");
                return;
            }

            // we wait her to the end of the External port
            switch (mainWaitLoop(controller_params)) {
                case Signal::quit:
                    run = false;
                    break;
                case Signal::restart:
                    XLOG::l.i("restart main loop");
                    if (!controller_params) {
                        break;
                    }
                    wtools::KillProcessesByFullPath(
                        fs::path{cfg::GetUserBinDir()} / cfg::files::kAgentCtl);
                    controller_params = OptionallyStartAgentController(1000ms);
                    break;
            }
        }

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

    thread_ = std::thread(&ServiceProcessor::mainThreadAsTest, this);
    XLOG::l.i("Successful start of main thread");
}

namespace {
struct MonitoringRequest {
    std::string text;
    std::string id;
};

std::optional<MonitoringRequest> GetMonitoringRequest(const YAML::Node &yaml) {
    try {
        auto y = yaml["monitoring_request"];
        return MonitoringRequest{.text{y["text"].as<std::string>()},
                                 .id{y["id"].as<std::string>()}};
    }

    catch (const std::exception & /*e*/) {
        return {};
    }
}

auto CalcTimePoint(const carrier::CarrierDataHeader *data_header) noexcept {
    const std::chrono::nanoseconds duration_since_epoch{
        data_header == nullptr ? 0U : data_header->answerId()};
    return std::chrono::time_point<std::chrono::steady_clock>{
        duration_since_epoch};
}

}  // namespace

void ServiceProcessor::processYamlInput(const std::string &yaml_text) noexcept {
    try {
        const auto y = YAML::Load(yaml_text);
        const auto mr = GetMonitoringRequest(y);
        if (mr.has_value()) {
            external_port_.putOnQueue(mr->text);
            XLOG::t.i("Request >{}< {} {}", yaml_text, mr->text, mr->id);
        } else {
            XLOG::l("Not supported request '{}'", yaml_text);
        }
    } catch (const std::exception &e) {
        XLOG::l("Invalid request '{}', exception: '{}'", yaml_text, e);
    }
}

bool SystemMailboxCallback(const mailslot::Slot * /*nothing*/, const void *data,
                           int len, void *context) {
    auto *processor = static_cast<srv::ServiceProcessor *>(context);
    if (processor == nullptr) {
        XLOG::l("error in param");
        return false;
    }

    switch (auto *dt = static_cast<const carrier::CarrierDataHeader *>(data);
            dt->type()) {
        case carrier::DataType::kLog:
            XLOG::l(XLOG::kNoPrefix)("[{}] {}", dt->providerId(),
                                     carrier::AsString(dt));
            break;
        case carrier::DataType::kSegment:
            XLOG::d.i("Received [{}] bytes from '{}'\n", len, dt->providerId());
            processor->addSectionToAnswer(dt->providerId(), CalcTimePoint(dt),
                                          carrier::AsDataBlock(dt));
            break;
        case carrier::DataType::kYaml:
            processor->processYamlInput(carrier::AsString(dt));
            break;
        case carrier::DataType::kCommand:
            if (auto rcp = commander::ObtainRunCommandProcessor();
                rcp != nullptr) {
                rcp(std::string{commander::kMainPeer}, carrier::AsString(dt));
            }

            break;
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
        STARTUPINFO si = {};
        si.cb = sizeof(STARTUPINFO);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = null_handle;
        ON_OUT_OF_SCOPE(CloseHandle(null_handle));

        PROCESS_INFORMATION pi = {};
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

/// - stops process
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
    ON_OUT_OF_SCOPE(::CloseHandle(handle));
    process_handle_ = wtools::InvalidHandle();

    // check status and kill process if required

    if (auto exit_code = STILL_ACTIVE;
        ::GetExitCodeProcess(handle, &exit_code) == FALSE ||  // no access
        exit_code == STILL_ACTIVE) {                          // running
        lk.unlock();

        // our process either running or we have no access to the
        // process
        // -> try to kill
        if (pid == 0) {
            XLOG::l.bp("Killing 0 process '{}' not allowed", name);
            return false;
        }

        if constexpr (wtools::kProcessTreeKillAllowed) {
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
