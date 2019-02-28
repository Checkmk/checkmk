
#include <stdafx.h>

#include <shlobj_core.h>

#include <chrono>
#include <cstdint>  // wchar_t when compiler options set weird

#include "tools/_process.h"

#include "common/mailslot_transport.h"
#include "common/wtools.h"

#include "yaml-cpp/yaml.h"

#include "external_port.h"
#include "service_processor.h"

namespace cma::srv {

// Implementation of the Windows signals

//

/*
void ServiceProcessor::processStarterThread() {
    XLOG::t("main Wait Loop");
    HANDLE job;
    cma::tools::RunStdCommandAsJob(
        job, L"C:\\ProgramData\\CheckMK\\Agent\\plugins\\delay120.cmd");
    while (1) {
        using namespace std::chrono;

        // wait and check
        std::unique_lock<std::mutex> l(lock_stopper_);
        auto stop_requested =
            stop_thread_.wait_until(l, steady_clock::now() + 1000ms,
                                    [this]() { return stop_requested_; });
        if (stop_requested) {
            XLOG::d("Stop request is set");
            break;  // signaled stop
        }
    }
    TerminateJobObject(job, 0);
    CloseHandle(job);
    XLOG::t("main Wait Loop END");
}
*/

void ServiceProcessor::startService() {
    if (thread_.joinable()) {
        xlog::l("Attempt to start service twice, no way!").print();
        return;
    }
    thread_ = std::thread(&ServiceProcessor::mainThread, this, &external_port_);
    /*
        process_thread_ =
            std::thread(&ServiceProcessor::processStarterThread, this);
    */
    XLOG::t("Successful start of thread");
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
void ServiceProcessor::pauseService() {}

// #TODO - implement
void ServiceProcessor::continueService() {}

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

    auto execute = GetArray<std::string>(groups::kGlobal, vars::kExecute);

    cma::FilterPathByExtension(files, execute);
    cma::RemoveDuplicatedNames(files);

    auto yaml_units = GetArray<YAML::Node>(cma::cfg::groups::kPlugins,
                                           cma::cfg::vars::kPluginsExecution);
    std::vector<Plugins::ExeUnit> exe_units;
    cma::cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);
}

// This is simple function which kicks to call
// different providers
int ServiceProcessor::startProviders(AnswerId Tp, std::string Ip) {
    using namespace cma::cfg;

    vf_.resize(0);
    max_timeout_ = 0;

#if 0
    vf_.emplace_back(txt_provider_.kick(Tp, this));
    if (0) vf_.emplace_back(file_provider_.kick(Tp, this));
#endif
    preLoadConfig();
    // sections to be kicked out
    tryToKick(uptime_provider_, Tp, Ip);
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
    auto& ohm_engine = ohm_provider_.getEngine();
    if (ohm_engine.isAllowedByCurrentConfig()) {
        if (!cma::tools::win::IsElevated()) {
            XLOG::d(
                "Starting OHM in non elevated mode has no sense. Please start it by self or change to the elevated mode");
        } else
            ohm_process_.start(cma::provider::GetOhmCliPath().wstring());
    }

    // WinPerf Processing
    if (groups::winperf.enabledInConfig() &&
        groups::global.allowedSection(vars::kWinPerfPrefixDefault)) {
        kickWinPerf(Tp, Ip);
    }

    // Plugins Processing
    if (0 && groups::plugins.enabledInConfig()) {
        cma::cfg::SetupPluginEnvironment();
        kickPlugins(Tp, Ip);
    }

    if (max_timeout_ <= 0) {
        max_timeout_ = cma::cfg::kDefaultAgentMinWait;
        XLOG::l.i("Max Timeout set to valid value {}", max_timeout_);
    }

    return static_cast<int>(vf_.size());
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
    XLOG::t("Received {} bytes from {}\n", Len, dt->providerId());
    switch (dt->type()) {
        case cma::carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            {
                std::string to_log;
                if (dt->data()) {
                    auto data = (const char*)dt->data();
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

// This Function is safe
bool TheMiniProcess::start(const std::wstring ExePath) {
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
        if (!::CreateProcess(ExePath.c_str(), nullptr, nullptr, nullptr, TRUE,
                             0, nullptr, nullptr, &si, &pi)) {
            XLOG::l("Failed to run {}", wtools::ConvertToUTF8(ExePath));
            return false;
        }
        process_handle_ = pi.hProcess;
        process_id_ = pi.dwProcessId;
        CloseHandle(pi.hThread);  // as in LA
        XLOG::d.i("Started {}", wtools::ConvertToUTF8(ExePath));
    }

    return true;
}

// returns true when killing occurs
bool TheMiniProcess::stop() {
    std::unique_lock lk(lock_);
    if (process_handle_ == INVALID_HANDLE_VALUE) return false;

    CloseHandle(process_handle_);
    process_handle_ = INVALID_HANDLE_VALUE;
    auto pid = process_id_;
    process_id_ = 0;

    // check status and reset handle if required
    DWORD exit_code = STILL_ACTIVE;
    if (!::GetExitCodeProcess(process_handle_, &exit_code) ||  // no access
        exit_code == STILL_ACTIVE) {                           // running

        // our proc either running or we have no access to the proc
        // try to kill
        lk.unlock();
        XLOG::l("Killing process {}", process_id_);
        wtools::KillProcessTree(pid);
        cma::tools::win::KillProcess(pid);
        return true;
    }
    return false;
}

}  // namespace cma::srv
