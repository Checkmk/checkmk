
#include "stdafx.h"

#include "service_processor.h"

#include <shlobj_core.h>

#include <chrono>
#include <cstdint>  // wchar_t when compiler options set weird

#include "commander.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "external_port.h"
#include "realtime.h"
#include "tools/_process.h"
#include "upgrade.h"
#include "yaml-cpp/yaml.h"

namespace cma::srv {

// Implementation of the Windows signals

// starter
void ServiceProcessor::startService() {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return;
    }

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

void ServiceProcessor::stopService() {
    XLOG::t(XLOG_FUNC + " called");
    {
        std::lock_guard lk(lock_stopper_);
        stop_requested_ = true;  // against spurious wake up
        stop_thread_.notify_one();
    }

    if (thread_.joinable()) thread_.join();
    if (process_thread_.joinable()) thread_.join();
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
    if (!thread_.joinable()) return;

    {
        std::lock_guard lk(lock_stopper_);
        stop_requested_ = true;  // against spurious wake up
        stop_thread_.notify_one();
    }
    thread_.join();
}

void ServiceProcessor::kickWinPerf(const AnswerId Tp, const std::string& Ip) {
    using namespace cma::cfg;

    auto cmd_line = groups::winperf.buildCmdLine();
    if (Ip.size())
        cmd_line = L"ip:" + wtools::ConvertToUTF16(Ip) + L" " + cmd_line;
    auto exe_name = groups::winperf.exe();
    if (cma::tools::IsEqual(exe_name, "agent")) {
        XLOG::t.i("Looking for default agent");
        namespace fs = std::filesystem;
        fs::path f = cma::cfg::GetRootDir();
        std::vector<fs::path> names = {
            f / cma::cfg::kDefaultAppFileName  // on install

        };

        // we can try 64 bit
        if (tgt::Is64bit()) names.emplace_back(f / "check_mk_service64.exe");

        names.emplace_back(f / "check_mk_service32.exe");

        exe_name.clear();
        for (const auto& name : names) {
            std::error_code ec;
            if (fs::exists(name, ec)) {
                exe_name = name.u8string();
                XLOG::d.i("Using file '{}' for winperf", exe_name);
                break;
            }
        }
        if (exe_name.empty()) {
            XLOG::l.crit("In folder '{}' not found binaries to exec winperf");
            return;
        }
    } else {
        XLOG::d.i("Looking for agent '{}'", exe_name);
    }
    auto wide_exe_name = wtools::ConvertToUTF16(exe_name);
    auto prefix = groups::winperf.prefix();
    auto timeout = groups::winperf.timeout();
    auto wide_prefix = wtools::ConvertToUTF16(prefix);

    vf_.emplace_back(kickExe(true,           // async ???
                             wide_exe_name,  // perf_counter.exe
                             Tp,             // answer id
                             this,           // context
                             wide_prefix,    // for section
                             timeout,        // in seconds
                             cmd_line));     // counters
    answer_.newTimeout(timeout);
}

void ServiceProcessor::kickPlugins(
    const AnswerId Tp,  // setting some environment variables for plugins
    const std::string& Ip) {
    using namespace cma::cfg;

    auto exe_name = groups::plugins.exeWide();

    auto cmd_line = groups::plugins.buildCmdLine();

    if (cmd_line.timeouts_.size() > 0) {
        auto max_t_out =
            *max_element(cmd_line.timeouts_.begin(), cmd_line.timeouts_.end());
        vf_.emplace_back(kickExe(true,                  // async ???
                                 exe_name,              // plugin_player.exe
                                 Tp,                    // answer id
                                 this,                  // context
                                 L"plugin",             // just unique name
                                 max_t_out,             // in seconds
                                 cmd_line.cmd_line_));  // plugins to exec

        // set timeout
        for (auto t_out : cmd_line.timeouts_) {
            answer_.newTimeout(t_out);
        }
    }
}

// usually called from the main entry point after connect came to us
// according to spec, we have to update stop time point and parameters from the
// config file
void ServiceProcessor::informDevice(cma::rt::Device& Device,
                                    std::string_view Ip) const noexcept {
    using namespace cma::cfg;

    if (!Device.started()) {
        XLOG::l("RT Device is not started");
        return;
    }

    if (!groups::global.realtimeEnabled()) {
        XLOG::t("Real time is disabled in config");
        return;
    }

    auto sections = groups::global.realtimeSections();
    if (sections.empty()) return;

    auto s_view = cma::tools::ToView(sections);

    auto rt_port = groups::global.realtimePort();
    auto password = groups::global.realtimePassword();
    auto rt_timeout = groups::global.realtimeTimeout();

    Device.connectFrom(Ip, rt_port, s_view, password);
}

// Global config reloaded here
// our list of plugins is GLOBAl
// so process it as global one
void ServiceProcessor::preLoadConfig() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");
    PathVector pv;
    for (auto& folder : groups::plugins.folders()) {
        pv.emplace_back(folder);
    }
    auto files = cma::GatherAllFiles(pv);

    auto execute = GetInternalArray(groups::kGlobal, vars::kExecute);

    cma::FilterPathByExtension(files, execute);
    cma::RemoveDuplicatedNames(files);

    auto yaml_units = GetArray<YAML::Node>(cma::cfg::groups::kPlugins,
                                           cma::cfg::vars::kPluginsExecution);
    std::vector<Plugins::ExeUnit> exe_units;
    cma::cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);
}

static void OptionallyReloadConfig() {
    // service may install cap, install ini or upgrade installation and
    // continue to work, config must be reloaded
    auto app_type = AppDefaultType();
    if (app_type == AppType::srv) {
        XLOG::l.i("Reloading config for SERVICE is required");
        cma::ReloadConfig();
        return;
    }

    XLOG::l.i("Reloading config for application type [{}] is NOT required",
              static_cast<int>(app_type));
}

void ServiceProcessor::preStart() {
    XLOG::l.i("Pre Start actions");

    OptionallyReloadConfig();
    //
    cma::cfg::SetupPluginEnvironment();
    ohm_started_ = conditionallyStartOhm();

    auto& plugins = plugins_provider_.getEngine();
    plugins.preStart();
    plugins.detachedStart();

    auto& local = local_provider_.getEngine();
    local.preStart();
    XLOG::l.i("Pre Start actions ended");
}

void ServiceProcessor::detachedPluginsStart() {
    XLOG::t.i("Detached Start");
    auto& plugins = plugins_provider_.getEngine();
    plugins.detachedStart();
}

void ServiceProcessor::resetOhm() noexcept {
    using namespace cma::cfg::upgrade;
    auto powershell_exe = cma::FindPowershellExe();
    if (powershell_exe.empty()) {
        XLOG::l("NO POWERSHELL!");
        return;
    }

    // terminating all
    wtools::KillProcess(cma::provider::ohm::kExeModuleWide, 1);
    StopWindowsService(cma::provider::ohm::kDriverNameWide);
    auto status = WaitForStatus(GetServiceStatusByName,
                                cma::provider::ohm::kDriverNameWide,
                                SERVICE_STOPPED, 5000);
    auto cmd_line = powershell_exe;
    cmd_line += L" ";
    cmd_line += std::wstring(cma::provider::ohm::kResetCommand);
    XLOG::l.i("I'm going to execute '{}'", wtools::ConvertToUTF8(cmd_line));

    cma::tools::RunStdCommand(cmd_line, true);
}

// conditions are: yml + exists(ohm) + elevated
// true on successful start or if OHM is already started
bool ServiceProcessor::conditionallyStartOhm() noexcept {
    using namespace cma::tools;

    auto& ohm_engine = ohm_provider_.getEngine();
    if (!ohm_engine.isAllowedByCurrentConfig()) {
        XLOG::t.i("OHM starting skipped due to config");
        return false;
    }

    if (!win::IsElevated()) {
        XLOG::d(
            "Starting OHM in non elevated mode has no sense."
            "Please start it by self or change to the elevated mode");
        return false;
    }

    auto ohm_exe = cma::provider::GetOhmCliPath();
    if (!IsValidRegularFile(ohm_exe)) {
        XLOG::d("OHM file '{}' is not found", ohm_exe.u8string());
        return false;
    }

    auto error_count = ohm_engine.errorCount();
    if (error_count > cma::cfg::kMaxOhmErrorsBeforeRestart) {
        XLOG::l(
            "Too many errors [{}] on the OHM, stopping, cleaning and starting",
            error_count);
        // no ohm, nop reset
        auto running = ohm_process_.running();
        if (running) ohm_process_.stop();

        resetOhm();

        ohm_engine.resetError();
        if (running) ohm_process_.start(ohm_exe.wstring());
    } else {
        if (!ohm_process_.running()) {
            XLOG::l.i("OHM is not running by Agent");
            if (wtools::FindProcess(cma::provider::ohm::kExeModuleWide)) {
                XLOG::l.i("OHM is found: REUSE running OHM");
                return true;
            }
        }
        ohm_process_.start(ohm_exe.wstring());
    }
    return true;
}

// This is relative simple function which kicks to call
// different providers
int ServiceProcessor::startProviders(AnswerId Tp, std::string Ip) {
    using namespace cma::cfg;

    vf_.clear();
    max_timeout_ = 0;

    preLoadConfig();
    // sections to be kicked out
    tryToKick(uptime_provider_, Tp, Ip);

    // #TODO remove warning and relocate this block back at the end after
    // beta-testing We have RElocated winperf here just to be compatible with
    // older servers to winperf check crash. This is not 100% guarantee, that we
    // get winperf before plugin winperf but good enough for older servers(which
    // we should not support in any case)
    //
    // WinPerf Processing
    if (groups::winperf.enabledInConfig() &&
        groups::global.allowedSection(vars::kWinPerfPrefixDefault)) {
        kickWinPerf(Tp, Ip);
    }

    tryToKick(df_provider_, Tp, Ip);
    tryToKick(mem_provider_, Tp, Ip);
    tryToKick(services_provider_, Tp, Ip);
    tryToKick(ps_provider_, Tp, Ip);
    tryToKick(fileinfo_provider_, Tp, Ip);
    tryToKick(logwatch_event_provider_, Tp, Ip);
    tryToKick(plugins_provider_, Tp, Ip);
    tryToKick(local_provider_, Tp, Ip);

    tryToKick(dotnet_clrmemory_provider_, Tp, Ip);
    tryToKick(wmi_cpuload_provider_, Tp, Ip);
    tryToKick(wmi_webservices_provider_, Tp, Ip);
    tryToKick(msexch_provider_, Tp, Ip);

    tryToKick(mrpe_provider_, Tp, Ip);
    tryToKick(skype_provider_, Tp, Ip);
    tryToKick(spool_provider_, Tp, Ip);
    tryToKick(ohm_provider_, Tp, Ip);
    // Plugins Processing
#if 0
    // we do not use anymore separate plugin process(player)
    // code is here as future refernce to use again separate process
    if (groups::plugins.enabledInConfig()) {
        cma::cfg::SetupPluginEnvironment();
        kickPlugins(Tp, Ip);
    }
#endif

    if (max_timeout_ <= 0) {
        max_timeout_ = cma::cfg::kDefaultAgentMinWait;
        XLOG::l.i("Max Timeout set to valid value [{}]", max_timeout_);
    } else
        XLOG::l.i("Max Timeout is [{}]", max_timeout_);

    return static_cast<int>(vf_.size());
}

// test function to be used when no real connection
void ServiceProcessor::sendDebugData() {
    XLOG::l.i("Started without IO. Debug mode");

    auto tp = openAnswer("127.0.0.1");
    if (!tp) return;
    auto started = startProviders(tp.value(), "");
    auto block = getAnswer(started);
    block.emplace_back('\0');  // yes, we need this for printf
    auto count = printf("%s", block.data());
    if (count != block.size() - 1) {
        XLOG::l("Binary data at offset [{}]", count);
    }
}

// called before every answer to execute routine tasks
void ServiceProcessor::prepareAnswer(const std::string& ip_from,
                                     cma::rt::Device& rt_device) {
    auto value = cma::tools::win::GetEnv(cma::kAutoReload);

    if (cma::cfg::ReloadConfigAutomatically() ||
        cma::tools::IsEqual(value, L"yes"))
        cma::ReloadConfig();

    cma::cfg::SetupRemoteHostEnvironment(ip_from);
    ohm_started_ = conditionallyStartOhm();  // start may happen when
                                             // config changed

    detachedPluginsStart();  // cmk agent update
    informDevice(rt_device, ip_from);
}

// main function of the client
cma::ByteVector ServiceProcessor::generateAnswer(const std::string& ip_from) {
    auto tp = openAnswer(ip_from);
    if (tp) {
        XLOG::d.i("Id is [{}] ", tp.value().time_since_epoch().count());
        auto count_of_started = startProviders(tp.value(), ip_from);

        return getAnswer(count_of_started);
    }

    XLOG::l.crit("Can't open Answer");
    return makeTestString("No Answer");
}

// <HOSTING THREAD>
// ex_port may be nullptr(command line test, for example)
// makes a mail slot + starts IO on TCP
void ServiceProcessor::mainThread(world::ExternalPort* ex_port) noexcept {
    using namespace std::chrono;
    // Periodically checks if the service is stopping.
    // mail slot name selector "service" or "not service"
    auto mailslot_name = cma::IsService() ? cma::cfg::kServiceMailSlot
                                          : cma::cfg::kTestingMailSlot;

#if 0
    // ARtificial memory allocator in thread
    std::vector<std::string> z;

    auto alloca = std::thread([&z]() {
        for (;;) {
            std::string s =
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
            s = s + s + s + s + s + s + s + s + s + s + s + s + s + s + s + s +
                s + s + s + s + s + s + s + s + s + s + s + s;
            s = s + s + s + s + s + s + s + s + s + s + s + s + s + s + s + s +
                s + s + s + s + s + s + s + s + s + s + s + s;
            s = s + s + s + s + s + s + s + s + s + s + s + s + s + s + s + s +
                s + s + s + s + s + s + s + s + s + s + s + s;
            s = s + s + s + s + s + s + s + s + s + s + s + s + s + s + s + s +
                s + s + s + s + s + s + s + s + s + s + s + s;
            z.push_back(s);
            ::Sleep(100);
        }
    });
#endif
    cma::MailSlot mailbox(mailslot_name, 0);
    using namespace cma::carrier;
    internal_port_ = BuildPortName(kCarrierMailslotName, mailbox.GetName());
    try {
        // start and stop for mailbox thread
        mailbox.ConstructThread(SystemMailboxCallback, 20, this);
        ON_OUT_OF_SCOPE(mailbox.DismantleThread());

        // preparation if any
        preStart();

        // check that we have something for testing
        if (ex_port == nullptr) {
            // wait for async plugins
            WaitForAsyncPluginThreads(5000ms);
            sendDebugData();
            return;
        }
        WaitForAsyncPluginThreads(5000ms);

        cma::rt::Device rt_device;
        for (;;) {
            // this is main processing loop
            rt_device.start();
            auto io_started = ex_port->startIo(
                [this,
                 &rt_device](const std::string Ip) -> std::vector<uint8_t> {
                    // most important entry point for external port io
                    // this is internal implementation of the io_context
                    // called upon kicking in port, i.e. LATER. NOT NOW.

                    prepareAnswer(Ip, rt_device);
                    XLOG::d.i("Generating answer number [{}]", answer_.num());
                    return generateAnswer(Ip);
                });
            ON_OUT_OF_SCOPE({
                ex_port->shutdownIo();
                rt_device.stop();
            });

            if (!io_started) {
                XLOG::l.bp("Ups. We cannot start main thread");
                return;
            }

            // we wait her to the end of the External port
            if (mainWaitLoop() == Signal::quit) break;
            XLOG::l.i("restart main loop");
        };

        // the end of the fun
        XLOG::l.i("Thread is stopped");
    } catch (const std::exception& e) {
        XLOG::l.crit("Not expected exception '{}'. Fix it!", e.what());
    } catch (...) {
        XLOG::l.bp("Not expected exception. Fix it!");
    }
    internal_port_ = "";
}

void ServiceProcessor::startTestingMainThread() {
    if (thread_.joinable()) {
        xlog::l("Attempt to start service twice, no way!").print();
        return;
    }
    thread_ = std::thread(&ServiceProcessor::mainThread, this, nullptr);
    XLOG::l(XLOG::kStdio)("Successful start of thread");
}

// Implementation of the Windows signals
// ---------------- END ----------------

bool SystemMailboxCallback(const cma::MailSlot* Slot, const void* Data, int Len,
                           void* Context) {
    using namespace std::chrono;
    auto processor = static_cast<cma::srv::ServiceProcessor*>(Context);
    if (!processor) {
        xlog::l("error in param\n");
        return false;
    }

    // your code is here

    auto fname = cma::cfg::GetCurrentLogFileName();

    auto dt = static_cast<const cma::carrier::CarrierDataHeader*>(Data);
    XLOG::d.i("Received [{}] bytes from '{}'\n", Len, dt->providerId());
    switch (dt->type()) {
        case cma::carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            {
                std::string to_log;
                if (dt->data()) {
                    auto data = static_cast<const char*>(dt->data());
                    to_log.assign(data, data + dt->length());
                    XLOG::l(XLOG::kNoPrefix)("{} : {}", dt->providerId(),
                                             to_log);
                } else
                    XLOG::l(XLOG::kNoPrefix)("{} : null", dt->providerId());
                break;
            }

        case cma::carrier::DataType::kSegment:
            // IMPORTANT ENTRY POINT
            // Receive data for Section
            {
                nanoseconds duration_since_epoch(dt->answerId());
                time_point<steady_clock> tp(duration_since_epoch);
                auto data_source = static_cast<const uint8_t*>(dt->data());
                auto data_end = data_source + dt->length();
                AsyncAnswer::DataBlock vectorized_data(data_source, data_end);

                if (vectorized_data.size() && vectorized_data.back() == 0) {
                    XLOG::l("Section '{}' sends null terminated strings",
                            dt->providerId());
                    vectorized_data.pop_back();
                }

                processor->addSectionToAnswer(dt->providerId(), tp,
                                              vectorized_data);
            }
            break;
        case cma::carrier::DataType::kYaml:
            XLOG::l.bp(XLOG_FUNC + " NOT SUPPORTED now");
            break;

        case cma::carrier::DataType::kCommand: {
            std::string cmd(static_cast<const char*>(dt->data()),
                            static_cast<size_t>(dt->length()));
            std::string peer(cma::commander::kMainPeer);
            cma::commander::RunCommand(peer, cmd);

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

// This Function is safe
bool TheMiniProcess::start(const std::wstring& exe_name) {
    std::unique_lock lk(lock_);
    if (process_handle_ != INVALID_HANDLE_VALUE) {
        // check status and reset handle if required
        DWORD exit_code = STILL_ACTIVE;
        if (!::GetExitCodeProcess(process_handle_, &exit_code) ||  // no access
            exit_code != STILL_ACTIVE) {                           // exit?
            if (exit_code != STILL_ACTIVE) {
                XLOG::l.i("Finished with {} code", exit_code);
            }
            CloseHandle(process_handle_);
            process_handle_ = INVALID_HANDLE_VALUE;
        }
    }

    if (process_handle_ == INVALID_HANDLE_VALUE) {
        auto null_handle = CreateDevNull();
        STARTUPINFO si{0};
        si.cb = sizeof(STARTUPINFO);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = null_handle;
        ON_OUT_OF_SCOPE(CloseHandle(null_handle));

        PROCESS_INFORMATION pi{0};
        if (!::CreateProcess(exe_name.c_str(), nullptr, nullptr, nullptr, TRUE,
                             0, nullptr, nullptr, &si, &pi)) {
            XLOG::l("Failed to run {}", wtools::ConvertToUTF8(exe_name));
            return false;
        }
        process_handle_ = pi.hProcess;
        process_id_ = pi.dwProcessId;
        CloseHandle(pi.hThread);  // as in LA

        process_name_ = wtools::ConvertToUTF8(exe_name);
        XLOG::d.i("Started '{}' wih pid [{}]", process_name_, process_id_);
    }

    return true;
}

// returns true when killing occurs
bool TheMiniProcess::stop() {
    std::unique_lock lk(lock_);
    if (process_handle_ == INVALID_HANDLE_VALUE) return false;

    auto name = process_name_;
    auto pid = process_id_;
    auto handle = process_handle_;

    process_id_ = 0;
    process_name_.clear();
    CloseHandle(handle);
    process_handle_ = INVALID_HANDLE_VALUE;

    // check status and reset handle if required
    DWORD exit_code = STILL_ACTIVE;
    if (!::GetExitCodeProcess(handle, &exit_code) ||  // no access
        exit_code == STILL_ACTIVE) {                  // running
        lk.unlock();

        // our process either running or we have no access to the process
        // -> try to kill
        if (pid == 0) {
            XLOG::l.bp("Killing 0 process '{}' not allowed", name);
            return false;
        }

        if (wtools::kProcessTreeKillAllowed) wtools::KillProcessTree(pid);

        wtools::KillProcess(pid);
        XLOG::l.t("Killing process [{}] '{}'", pid, name);
        return true;
    }

    XLOG::l.t("Process [{}] '{}' already dead", pid, name);
    return false;
}

}  // namespace cma::srv
