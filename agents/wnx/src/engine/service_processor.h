// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef service_processor_h__
#define service_processor_h__

#include <fmt/format.h>

#include <chrono>      // timestamps
#include <cstdint>     // wchar_t when compiler options set weird
#include <functional>  // callback in the main function
#include <future>      // std::async
#include <mutex>       //
#include <optional>    //
#include <thread>      //

#include "async_answer.h"
#include "carrier.h"
#include "cfg.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "external_port.h"
#include "logger.h"
#include "modules.h"
#include "providers/check_mk.h"
#include "providers/df.h"
#include "providers/fileinfo.h"
#include "providers/logwatch_event.h"
#include "providers/mem.h"
#include "providers/mrpe.h"
#include "providers/ohm.h"
#include "providers/p_perf_counters.h"
#include "providers/plugins.h"
#include "providers/ps.h"
#include "providers/services.h"
#include "providers/skype.h"
#include "providers/spool.h"
#include "providers/system_time.h"
#include "providers/wmi.h"
#include "read_file.h"
#include "realtime.h"
#include "tools/_win.h"

namespace cma::srv {
// mini processes of the global type
class TheMiniProcess {
public:
    TheMiniProcess() = default;

    TheMiniProcess(const TheMiniProcess &) = delete;
    TheMiniProcess &operator=(const TheMiniProcess &) = delete;
    TheMiniProcess(TheMiniProcess &&) = delete;
    TheMiniProcess &operator=(TheMiniProcess &&) = delete;

    ~TheMiniProcess() { stop(); }
    bool start(const std::wstring &exe_name);
    bool stop();
    bool running() const {
        std::lock_guard lk(lock_);
        return process_id_ != 0;
    }

private:
    mutable std::mutex lock_;
    HANDLE process_handle_{wtools::InvalidHandle()};
    HANDLE thread_handle_{wtools::InvalidHandle()};
    uint32_t process_id_{0};
    std::string process_name_;  // for debug purposes

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class SectionProviderOhm;
    FRIEND_TEST(SectionProviderOhm, StartStopIntegration);
#endif
};

// ASSORTED
constexpr const wchar_t *kMainLogName = L"cmk_service.log";

bool SystemMailboxCallback(const cma::MailSlot *, const void *data, int len,
                           void *context);

class ServiceProcessor;

//
// wrapper to use section engine ASYNCHRONOUS by default
//
template <typename T>
class SectionProvider {
public:
    // engine is default constructed
    SectionProvider() { provider_uniq_name_ = engine_.getUniqName(); }

    // with engine init
    SectionProvider(const std::string &uniq_name,  // id for the provider
                    char separator)
        : engine_(uniq_name, separator) {
        provider_uniq_name_ = engine_.getUniqName();
    }

    std::future<bool> kick(
        std::launch mode,             // type of execution
        const std::string &cmd_line,  // command line, first is Ip address
        AnswerId answer_id,           // expected id
        ServiceProcessor *processor   // hosting object
    ) {
        engine_.registerOwner(processor);
        engine_.loadConfig();

        section_expected_timeout_ = engine_.timeout();
        return std::async(
            mode,
            [this](const std::string command_line,  //
                   const AnswerId answer_id,        //
                   const ServiceProcessor *Proc) {
                engine_.updateSectionStatus();  // actual data gathering is
                                                // here for plugins and local

                engine_.registerCommandLine(command_line);
                auto port_name = Proc->getInternalPort();
                auto id = AnswerIdToNumber(answer_id);
                XLOG::d.t(
                    "Provider '{}' is about to be started, id '{}' port [{}]",
                    provider_uniq_name_, id, port_name);
                goGoGo(std::string(section::kUseEmbeddedName), command_line,
                       port_name, id);

                return true;
            },
            cmd_line,   //
            answer_id,  // param 1
            processor   // param 2

        );
    }

    // used to call complicated providers directly without any threads
    // to obtain maximally correct results
    bool directCall(
        const std::string &cmd_line,  // command line, first is Ip address
        AnswerId timestamp,           // expected id
        const std::string &port_name  // port to report results
    ) {
        engine_.loadConfig();
        section_expected_timeout_ = engine_.timeout();
        engine_.updateSectionStatus();
        engine_.registerCommandLine(cmd_line);
        auto id = AnswerIdToNumber(timestamp);
        XLOG::d.t("Provider '{}' is direct called, id '{}' port [{}]",
                  provider_uniq_name_, id, port_name);
        goGoGo(std::string(section::kUseEmbeddedName), cmd_line, port_name, id);

        return true;
    }

    const T &getEngine() const { return engine_; }
    T &getEngine() { return engine_; }

    int expectedTimeout() const { return section_expected_timeout_; }

protected:
    std::string provider_uniq_name_;
    T engine_;
    int section_expected_timeout_ = 0;

    void goGoGo(const std::string &section_name,  //
                const std::string &command_line,  //
                const std::string &port,          //
                uint64_t marker) {                // std marker
        engine_.stopWatchStart();
        auto cmd_line =
            fmt::format("{} {} {}", marker, section_name, command_line);

        engine_.startExecution(port, cmd_line);
        auto us_count = engine_.stopWatchStop();
        XLOG::d.i("perf: Section '{}' took [{}] milliseconds",
                  provider_uniq_name_, us_count / 1000);
    }
};

// Implements main logic related to interaction: "Agent <-> Plugins"
// non movable, non copyable
// Thread Safe
class ServiceProcessor : public wtools::BaseServiceProcessor {
public:
    using thread_callback = std::function<bool(const void *)>;
    using AnswerDataBlock = cma::srv::AsyncAnswer::DataBlock;
    ServiceProcessor(std::chrono::milliseconds delay, thread_callback callback)
        : delay_(delay), callback_(callback), external_port_(this) {}
    ServiceProcessor() : external_port_(this) {
        using namespace std::chrono_literals;
        delay_ = 1000ms;
    }
    ~ServiceProcessor() { ohm_process_.stop(); }

    // boiler plate
    ServiceProcessor(const ServiceProcessor &Rhs) = delete;
    ServiceProcessor &operator=(ServiceProcessor &Rhs) = delete;
    ServiceProcessor(const ServiceProcessor &&Rhs) = delete;
    ServiceProcessor &operator=(ServiceProcessor &&Rhs) = delete;

    // Standard Windows API to Service
    void stopService();
    void startService();
    void pauseService();
    void shutdownService();
    void continueService();

    // \brief - serves test in command line
    void startServiceAsLegacyTest();

    void cleanupOnStop() override;

    const wchar_t *getMainLogName() const { return kMainLogName; }

    const std::string getInternalPort() const noexcept {
        return internal_port_;
    }

    // functions for testing/verifying
    void startTestingMainThread();
    void stopTestingMainThread();

    // called by callbacks from Internal Transport section providers
    bool addSectionToAnswer(const std::string &name, const AnswerId timestamp,
                            const AsyncAnswer::DataBlock &data) {
        return answer_.addSegment(name, timestamp, data);
    }

    // called when no data for section generated - this is ok
    bool addSectionToAnswer(const std::string &name, const AnswerId timestamp) {
        return answer_.addSegment(name, timestamp, std::vector<uint8_t>());
    }

    static void resetOhm() noexcept;
    bool isOhmStarted() const noexcept { return ohm_started_; }

    cma::cfg::modules::ModuleCommander &getModuleCommander() noexcept {
        return mc_;
    }
    const cma::cfg::modules::ModuleCommander &getModuleCommander()
        const noexcept {
        return mc_;
    }

private:
    std::vector<uint8_t> makeTestString(const char *text) {
        const std::string answer_test{text == nullptr ? "" : text};
        std::vector<uint8_t> answer_vector{answer_test.begin(),
                                           answer_test.end()};
        return answer_vector;
    }

    // controlled exclusively by mainThread
    std::string internal_port_;

    cma::cfg::modules::ModuleCommander mc_;

    // called by external port BEFORE starting context run
    // on this phase we are starting our async plugins
    void preContextCall() {}

    void informDevice(cma::rt::Device &Device,
                      std::string_view Ip) const noexcept;

    // used to start OpenHardwareMonitor if conditions are ok
    bool stopRunningOhmProcess() noexcept;
    [[nodiscard]] bool conditionallyStartOhm() noexcept;
    void mainThread(world::ExternalPort *Port) noexcept;

    // object data
    std::thread thread_;
    std::thread rm_lwa_thread_;
    std::thread process_thread_;
    std::mutex lock_;  // data lock
    std::chrono::milliseconds delay_;

    // stopping code
    std::condition_variable stop_thread_;
    std::mutex lock_stopper_;
    bool stop_requested_ = false;
    thread_callback callback_ = [](const void *) { return true; };  // nothing

    uint16_t working_port_ = cma::cfg::kMainPort;

    // First Class Objects
    cma::world::ExternalPort external_port_;
    AsyncAnswer &getAsyncAnswer() { return answer_; }

private:
    bool ohm_started_ = false;
    // support of mainThread
    void prepareAnswer(const std::string &ip_from, cma::rt::Device &rt_device);
    cma::ByteVector generateAnswer(const std::string &ip_from);
    void sendDebugData();

    bool timedWaitForStop() {
        std::unique_lock<std::mutex> l(lock_stopper_);
        auto stop_requested = stop_thread_.wait_until(
            l, std::chrono::steady_clock::now() + delay_,
            [this]() { return stop_requested_; });
        return stop_requested;
    }

    bool restartBinariesIfCfgChanged(uint64_t &last_cfg_id);

    // type of breaks in mainWaitLoop
    enum class Signal { restart, quit };

    // returns break type(what todo)
    Signal mainWaitLoop();

    AsyncAnswer answer_;  // queue in the future, now only one answer for all

    std::vector<std::future<bool>> vf_;

    // called from the network callbacks in ExternalPort
    std::optional<AnswerId> openAnswer(const std::string &ip_addr) {
        using namespace std::chrono_literals;
        if (answer_.isAnswerInUse() &&
            !answer_.isAnswerOlder(60s))  // answer is in process
        {
            XLOG::l("Answer is in use and too young - to be fixed");
            return {};
        }

        answer_.dropAnswer();
        answer_.prepareAnswer(ip_addr);
        return answer_.getId();
    }

    //
    int startProviders(AnswerId timestamp, const std::string &ip_addr);

    // all pre operation required for normal functionality
    void preStartBinaries();
    void detachedPluginsStart();

private:
    TheMiniProcess ohm_process_;
    void updateMaxWaitTime(int timeout_seconds) noexcept;
    void checkMaxWaitTime() noexcept;
    std::mutex max_wait_time_lock_;
    int max_wait_time_;  // this is waiting time for all section to run

    template <typename T>
    bool isAllowed(const T &engine) {
        // check time
        auto allowed_by_time = engine.isAllowedByTime();
        if (!allowed_by_time) {
            XLOG::d.t("Skipping '{}' by time", engine.getUniqName());
            return false;
        }

        // check config
        auto allowed = engine.isAllowedByCurrentConfig();
        if (!allowed) {
            XLOG::d.t("Skipping '{}' by config", engine.getUniqName());
            return false;
        }

        return true;
    }

    template <typename T>
    bool tryToKick(T &section_provider, AnswerId stamp,
                   const std::string &cmdline) {
        const auto &engine = section_provider.getEngine();

        if (!isAllowed(engine)) return false;

        // success story...
        vf_.emplace_back(
            section_provider.kick(std::launch::async, cmdline, stamp, this));
        auto expected_timeout = section_provider.expectedTimeout();
        updateMaxWaitTime(expected_timeout);

        return true;
    }

    template <typename T>
    bool tryToDirectCall(T &section_provider, AnswerId stamp,
                         const std::string &cmdline) {
        const auto &engine = section_provider.getEngine();

        if (!isAllowed(engine)) return false;

        // success story...
        section_provider.directCall(cmdline, stamp, getInternalPort());

        return true;
    }

    void kickWinPerf(AnswerId answer_id, const std::string &ip_addr);

    template <typename T>
    std::string generate() {
        static_assert(std::is_base_of<cma::provider::Synchronous, T>::value,
                      "Must be Synchronous based");
        T section;
        section.updateSectionStatus();
        return section.generateContent();
    }

    /// \brief wraps resulting data with CheckMk and SystemTime sections
    ///
    /// Answer must be build in specific order:
    /// pre sections[s] - usually Check_MK
    /// body from answer
    /// post sections[s]- usually SystemTime
    AnswerDataBlock wrapResultWithStaticSections(const AnswerDataBlock &block) {
        // pre sections generation
        auto pre = generate<provider::CheckMk>();
        auto post = generate<provider::SystemTime>();

        // concatenating
        AnswerDataBlock result;
        try {
            result.reserve(pre.size() + block.size() + post.size());

            result.insert(result.end(), pre.begin(), pre.end());
            result.insert(result.end(), block.begin(), block.end());
            result.insert(result.end(), post.begin(), post.end());
        } catch (std::exception &e) {
            XLOG::l.crit(XLOG_FUNC + "Weird exception '{}'", e.what());
        }

        return result;
    }

    void logAnswerProcessing(bool success) {
        auto get_segments_text = [this]() -> std::string {
            auto list = answer_.segmentNameList();
            std::string s;
            for (auto const &l : list) {
                s += " " + l;
            }
            return s;
        };

        if (success) {
            XLOG::t(XLOG_FLINE + " full answer: \n\t {}",
                    get_segments_text());  // on the hand

        } else {
            XLOG::l(XLOG_FLINE +
                        " no full answer: awaited [{}], received [{}]\n\t {}",
                    answer_.awaitingSegments(),  // expected count
                    answer_.receivedSegments(),
                    get_segments_text());  // on the hand
        }

        XLOG::d.i("perf: Answer is ready in [{}] milliseconds",
                  answer_.getStopWatch().getUsCount() / 1000);
    }

    /// \brief wait for all answers from all providers
    /// The call is *blocking*
    AsyncAnswer::DataBlock getAnswer(int count) {
        XLOG::t.i("waiting futures(only start)");

        int future_count = 0;
        auto start_point = std::chrono::steady_clock::now();

        // NOTE: here we are starting futures, i.e. just fire all
        // futures in C++ kind of black magic, do not care too much
        for_each(vf_.begin(), vf_.end(),  // scan future array
                 [&future_count](std::future<bool> &x) {
                     // kill future
                     x.get();
                     ++future_count;
                 });

        auto end_point = std::chrono::steady_clock::now();
        XLOG::t.i(
            "futures ready in {} milliseconds",
            duration_cast<std::chrono::milliseconds>(end_point - start_point)
                .count());

        // set count of started to await for answer
        // count is from startProviders
        answer_.exeKickedCount(count);
        auto success = answer_.waitAnswer(std::chrono::seconds{max_wait_time_});
        logAnswerProcessing(success);
        auto result = std::move(answer_.getDataAndClear());
        return wrapResultWithStaticSections(result);
    }

    class SectionProviderText {
    public:
        SectionProviderText(const std::string &name, const std::string &text)
            : name_(name), text_(text) {}

        std::future<bool> kick(AnswerId stamp, ServiceProcessor *proc) {
            return std::async(
                std::launch::async,
                [this](const AnswerId stamp, ServiceProcessor *proc) {
                    auto block = gatherData();
                    if (block) {
                        XLOG::d("Provider '{}' added answer", name_);
                        return proc->addSectionToAnswer(name_, stamp, *block);
                    } else {
                        XLOG::l("Provider '{}' FAILED answer", name_);
                        proc->addSectionToAnswer(name_, stamp);
                        return false;
                    }
                },
                stamp,  // param 1
                proc    // param 2

            );
        }

    private:
        std::string name_;
        std::string text_;
        std::optional<std::vector<uint8_t>> gatherData() {
            return std::vector<uint8_t>{text_.begin(), text_.end()};
        }
    };

    class SectionProviderFile {
    public:
        SectionProviderFile(const std::string name, const std::wstring filename)
            : name_(name), file_name_(filename) {}

        std::future<bool> kick(const AnswerId answer_id,
                               ServiceProcessor *service_processor) {
            return std::async(
                std::launch::async,
                [this](const AnswerId answer_id,
                       ServiceProcessor *service_processor) {
                    auto block = gatherData();
                    if (!block) {
                        return false;
                    }

                    XLOG::l.i("Provider '{}' added answer to file '{}'", name_,
                              wtools::ToUtf8(file_name_));
                    return service_processor->addSectionToAnswer(
                        name_, answer_id, *block);
                },
                answer_id,         // param 1
                service_processor  // param 2

            );
        }

    private:
        std::string name_;
        std::wstring file_name_;
        std::optional<std::vector<uint8_t>> gatherData() {
            auto f = cfg::FindExeFileOnPath(file_name_);
            return tools::ReadFileInVector(file_name_.c_str());
        }
    };

    void logExeNotFound(std::wstring_view exe_name) {
        std::string path_string;
        auto paths = cfg::GetExePaths();
        for (const auto &dir : paths) {
            path_string += dir.u8string() + "\n";
        }

        XLOG::l("File '{}' not found on the path '{}'",
                wtools::ToUtf8(exe_name), path_string);
    }

    // starting executable(any!) with valid command line
    // API to start exe
    std::future<bool> kickExe(
        bool async_mode,                      // controlled from the config
        const std::wstring exe_name,          //
        AnswerId answer_id,                   //
        ServiceProcessor *service_processor,  // host
        const std::wstring &segment_name,     // identifies exe
        int timeout,                          // for exe
        const std::wstring &command_line,     //
        const std::wstring &log_file) {       // this is optional
        return std::async(
            async_mode ? std::launch::async : std::launch::deferred,
            [this, exe_name, log_file](
                AnswerId answer_id, ServiceProcessor *service_processor,
                const std::wstring &segment_name, int timeout,
                const std::wstring &command_line) {
                // finding and checking
                XLOG::d.i("Exec '{}' for '{}' to be started",
                          wtools::ToUtf8(exe_name),
                          wtools::ToUtf8(segment_name));

                auto full_path = cfg::FindExeFileOnPath(exe_name);
                if (full_path.empty()) {
                    logExeNotFound(exe_name);
                    return false;
                }

                // make command line
                auto port = wtools::ConvertToUTF16(
                    service_processor->getInternalPort());
                auto cmd_line =
                    fmt::format(L"\"{}\" -runonce {}{} {} id:{} timeout:{} {}",
                                full_path,  // exe
                                log_file.empty() ? L"" : L"@" + log_file + L" ",
                                segment_name,                 //
                                port,                         //
                                AnswerIdToNumber(answer_id),  // answer id
                                timeout, command_line);

                // execution
                XLOG::d.i("async RunStdCmd: {}", wtools::ToUtf8(cmd_line));
                auto ret = tools::RunStdCommand(cmd_line, false);
                if (ret == 0) {
                    XLOG::l("Exec is failed with error [{}]", ::GetLastError());
                    return false;
                }

                return true;
            },
            answer_id,          // param 1
            service_processor,  // param 2
            segment_name,       // section name
            timeout,            //
            command_line

        );
    }

    std::future<bool> kickExe(
        bool async,                           // controlled from the config
        const std::wstring exe_name,          //
        const AnswerId answer_id,             //
        ServiceProcessor *service_processor,  // host
        const std::wstring &segment_name,     // identifies exe
        int timeout,                          // for exe
        const std::wstring &command_line) {
        return kickExe(async, exe_name, answer_id, service_processor,
                       segment_name, timeout, command_line, {});
    }

    // Dynamic Internal sections
    SectionProvider<provider::UptimeAsync> uptime_provider_;
    SectionProvider<provider::Df> df_provider_;
    SectionProvider<provider::Mem> mem_provider_;
    SectionProvider<provider::Services> services_provider_;
    SectionProvider<provider::Ps> ps_provider_;
    SectionProvider<provider::FileInfo> fileinfo_provider_;
    SectionProvider<provider::LogWatchEvent> logwatch_event_provider_;
    SectionProvider<provider::PluginsProvider> plugins_provider_;
    SectionProvider<provider::LocalProvider> local_provider_;

    SectionProvider<provider::MrpeProvider> mrpe_provider_;
    SectionProvider<provider::SkypeProvider> skype_provider_;
    SectionProvider<provider::OhmProvider> ohm_provider_{
        provider::kOhm, provider::ohm::kSepChar};
    SectionProvider<provider::SpoolProvider> spool_provider_;

    SectionProvider<provider::Wmi> dotnet_clrmemory_provider_{
        provider::kDotNetClrMemory, cma::provider::wmi::kSepChar};

    SectionProvider<provider::Wmi> wmi_webservices_provider_{
        provider::kWmiWebservices, cma::provider::wmi::kSepChar};

    SectionProvider<provider::Wmi> msexch_provider_{
        provider::kMsExch, cma::provider::wmi::kSepChar};

    SectionProvider<provider::Wmi> wmi_cpuload_provider_{
        provider::kWmiCpuLoad, cma::provider::wmi::kSepChar};

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ServiceProcessorTest;
    FRIEND_TEST(ServiceProcessorTest, StartStopExe);
    FRIEND_TEST(ServiceProcessorTest, Generate);

    friend class SectionProviderOhm;
    FRIEND_TEST(SectionProviderOhm, ConditionallyStartOhmIntegration);

    friend class CmaCfg;
    FRIEND_TEST(CmaCfg, RestartBinaries);

    friend class ServiceProcessorTest;
    FRIEND_TEST(ServiceProcessorTest, Base);

#endif
};

// tested indirectly in integration
// gtest is required
template <typename T, typename B>
void WaitForAsyncPluginThreads(std::chrono::duration<T, B> allowed_wait) {
    using namespace std::chrono;

    cma::tools::sleep(500ms);  // giving a bit time to start threads
    auto count = cma::PluginEntry::threadCount();
    XLOG::d.i("Waiting for async threads [{}]", count);
    constexpr auto grane = 500ms;
    auto wait_time = allowed_wait;

    // waiting is like a polling
    // we do not want to loose time on test method
    while (wait_time >= 0ms) {
        int count = cma::PluginEntry::threadCount();
        if (count == 0) break;

        cma::tools::sleep(grane);
        wait_time -= grane;
    }
    count = cma::PluginEntry::threadCount();
    XLOG::d.i("Left async threads [{}] after waiting {}ms", count,
              (allowed_wait - wait_time).count());
}

}  // namespace cma::srv

#endif  // service_processor_h__
