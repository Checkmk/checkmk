
// provides basic api to start and stop service

#pragma once
#ifndef service_processor_h__
#define service_processor_h__

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
#include "fmt/format.h"
#include "logger.h"
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
#include "tools/_xlog.h"

namespace cma::srv {
// mini processes of the global type
class TheMiniProcess {
public:
    TheMiniProcess()
        : process_handle_(INVALID_HANDLE_VALUE)
        , thread_handle_(INVALID_HANDLE_VALUE)
        , process_id_(0) {}

    TheMiniProcess(const TheMiniProcess&) = delete;
    TheMiniProcess& operator=(const TheMiniProcess&) = delete;
    TheMiniProcess(TheMiniProcess&&) = delete;
    TheMiniProcess& operator=(TheMiniProcess&&) = delete;

    ~TheMiniProcess() { stop(); }
    bool start(const std::wstring& exe_name);
    bool stop();
    bool running() const {
        std::lock_guard lk(lock_);
        return process_id_ != 0;
    }

private:
    mutable std::mutex lock_;
    HANDLE process_handle_;
    HANDLE thread_handle_;
    uint32_t process_id_;
    std::string process_name_;  // for debug purposes

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class SectionProviderOhm;
    FRIEND_TEST(SectionProviderOhm, StartStop);
#endif
};

// ASSORTED
constexpr const wchar_t* kMainLogName = L"cmk_service.log";

bool SystemMailboxCallback(const cma::MailSlot*, const void* data, int len,
                           void* context);

class ServiceProcessor;

// wrapper to use section engine ASYNCHRONOUS by default
//
template <typename T>
class SectionProvider {
public:
    // engine is default constructed
    SectionProvider() { provider_uniq_name_ = engine_.getUniqName(); }

    // with engine init
    SectionProvider(const std::string& uniq_name,  // id for the provider
                    char separator)
        : engine_(uniq_name, separator) {
        provider_uniq_name_ = engine_.getUniqName();
    }

    // #TODO this function is not simple enough
    std::future<bool> kick(
        std::launch mode,             // type of execution
        const std::string& cmd_line,  // command line, first is Ip address
        const AnswerId Tp,            // expected id
        ServiceProcessor* processor   // hosting object
    ) {
        engine_.loadConfig();
        section_expected_timeout_ = engine_.timeout();
        return std::async(
            mode,
            [this](const std::string CommandLine,  //
                   const AnswerId Tp,              //
                   const ServiceProcessor* Proc) {
                engine_.updateSectionStatus();  // actual data gathering is here
                                                // for plugins and local

                engine_.registerCommandLine(CommandLine);
                auto port_name = Proc->getInternalPort();
                auto id = Tp.time_since_epoch().count();
                XLOG::d.t(
                    "Provider '{}' is about to be started, id '{}' port [{}]",
                    provider_uniq_name_, id, port_name);
                goGoGo(std::string(section::kUseEmbeddedName), CommandLine,
                       port_name, id);

                return true;
            },
            cmd_line,  //
            Tp,        // param 1
            processor  // param 2

        );
    }

    // used to call complicated providers directly without any threads
    // to obtain maximally correct results
    bool directCall(
        const std::string& cmd_line,  // command line, first is Ip address
        const AnswerId timestamp,     // expected id
        const std::string& port_name  // port to report results
    ) {
        engine_.loadConfig();
        section_expected_timeout_ = engine_.timeout();
        engine_.updateSectionStatus();
        engine_.registerCommandLine(cmd_line);
        auto id = timestamp.time_since_epoch().count();
        XLOG::d.t("Provider '{}' is direct called, id '{}' port [{}]",
                  provider_uniq_name_, id, port_name);
        goGoGo(std::string(section::kUseEmbeddedName), cmd_line, port_name, id);

        return true;
    }

    const T& getEngine() const { return engine_; }
    T& getEngine() { return engine_; }

    int expectedTimeout() const { return section_expected_timeout_; }

protected:
    std::string provider_uniq_name_;
    T engine_;
    int section_expected_timeout_ = 0;

    void goGoGo(const std::string& SectionName,  //
                const std::string& CommandLine,  //
                const std::string& Port,         //
                uint64_t Marker) {               // std marker
        engine_.stopWatchStart();
        auto cmd_line =
            std::to_string(Marker) + " " + SectionName + " " + CommandLine;

        engine_.startSynchronous(Port, cmd_line);
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
    using thread_callback = std::function<bool(const void*)>;
    using AnswerDataBlock = cma::srv::AsyncAnswer::DataBlock;
    ServiceProcessor(std::chrono::milliseconds Delay, thread_callback Callback)
        : delay_(Delay), callback_(Callback), external_port_(this) {}
    ServiceProcessor() : external_port_(this) {
        using namespace std::chrono;
        delay_ = 1000ms;
    }
    ~ServiceProcessor() { ohm_process_.stop(); }

    // boiler plate
    ServiceProcessor(const ServiceProcessor& Rhs) = delete;
    ServiceProcessor& operator=(ServiceProcessor& Rhs) = delete;
    ServiceProcessor(const ServiceProcessor&& Rhs) = delete;
    ServiceProcessor& operator=(ServiceProcessor&& Rhs) = delete;

    // Standard Windows API to Service
    // our callbacks withing processor:
    void stopService();

    // true will generate one call without external port usage
    void startService();
    void startServiceAsLegacyTest();
    void pauseService();
    void shutdownService();
    void continueService();

    // we are good engineers
    const wchar_t* getMainLogName() const { return cma::srv::kMainLogName; }

    // internal port means internal transport
    const std::string getInternalPort() const noexcept {
        return internal_port_;
    }

    // functions for testing/verifying
    void startTestingMainThread();
    void stopTestingMainThread();

    // called by callbacks from Internal Transport section providers
    bool addSectionToAnswer(const std::string& name, const AnswerId timestamp,
                            const AsyncAnswer::DataBlock& data) {
        return answer_.addSegment(name, timestamp, data);
    }

    // called when no data for section generated - this is ok
    bool addSectionToAnswer(const std::string& name, const AnswerId timestamp) {
        return answer_.addSegment(name, timestamp, std::vector<uint8_t>());
    }

    static void resetOhm() noexcept;
    bool isOhmStarted() const noexcept { return ohm_started_; }

private:
    std::vector<uint8_t> makeTestString(const char* Text) {
        const std::string answer_test = Text;
        std::vector<uint8_t> answer_vector;
        answer_vector.assign(answer_test.begin(), answer_test.end());
        return answer_vector;
    }

    // controlled exclusively by mainThread
    std::string internal_port_;

    // called by external port BEFORE starting context run
    // on this phase we are starting our async plugins
    void preContextCall() {}

    void informDevice(cma::rt::Device& Device, std::string_view Ip) const
        noexcept;

    // used to start OpenHardwareMonitor if conditions are ok
    bool stopRunningOhmProcess() noexcept;
    [[nodiscard]] bool conditionallyStartOhm() noexcept;
    void mainThread(world::ExternalPort* Port) noexcept;

    // object data
    std::thread thread_;
    std::thread process_thread_;
    std::mutex lock_;  // data lock
    std::chrono::milliseconds delay_;

    // stopping code
    std::condition_variable stop_thread_;
    std::mutex lock_stopper_;
    bool stop_requested_ = false;
    thread_callback callback_ = [](const void*) { return true; };  // nothing

    uint16_t working_port_ = cma::cfg::kMainPort;

    // First Class Objects
    cma::world::ExternalPort external_port_;
    AsyncAnswer& getAsyncAnswer() { return answer_; }

private:
    bool ohm_started_ = false;
    // support of mainThread
    void prepareAnswer(const std::string& ip_from, cma::rt::Device& rt_device);
    cma::ByteVector generateAnswer(const std::string& ip_from);
    void sendDebugData();

    bool timedWaitForStop() {
        std::unique_lock<std::mutex> l(lock_stopper_);
        auto stop_requested = stop_thread_.wait_until(
            l, std::chrono::steady_clock::now() + delay_,
            [this]() { return stop_requested_; });
        return stop_requested;
    }

    bool restartBinariesIfCfgChanged(uint64_t& last_cfg_id);

    // type of breaks in mainWaitLoop
    enum class Signal { restart, quit };

    // returns break type(what todo)
    Signal mainWaitLoop();

    AsyncAnswer answer_;  // queue in the future, now only one answer for all

    std::vector<std::future<bool>> vf_;

    // called from the network callbacks in ExternalPort
    std::optional<AnswerId> openAnswer(const std::string ip_addr) {
        // race condition below
        using namespace std::chrono;
        if (answer_.isAnswerInUse() &&
            !answer_.isAnswerOlder(60s))  // answer is in process
        {
            XLOG::l("Answer is in use and too young - to be fixed");
            return {};  // #TODO make async here
        }

        // answer may be reused
        answer_.dropAnswer();
        answer_.prepareAnswer(ip_addr);  // is temporary
        auto tp = answer_.getId();

        return tp;
    }

    //
    int startProviders(AnswerId timestamp, const std::string& ip_addr);

    // all pre operation required for normal functionality
    void preStartBinaries();
    void detachedPluginsStart();

private:
    void preLoadConfig();
    TheMiniProcess ohm_process_;
    void updateMaxWaitTime(int timeout_seconds) noexcept;
    void checkMaxWaitTime() noexcept;
    std::mutex max_wait_time_lock_;
    int max_wait_time_;  // this is waiting time for all section to run

    template <typename T>
    bool isAllowed(const T& engine) {
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
    bool tryToKick(T& section_provider, AnswerId stamp,
                   const std::string& cmdline) {
        const auto& engine = section_provider.getEngine();

        if (!isAllowed(engine)) return false;

        // success story...
        vf_.emplace_back(
            section_provider.kick(std::launch::async, cmdline, stamp, this));
        auto expected_timeout = section_provider.expectedTimeout();
        updateMaxWaitTime(expected_timeout);

        return true;
    }

    template <typename T>
    bool tryToDirectCall(T& section_provider, AnswerId stamp,
                         const std::string& cmdline) {
        const auto& engine = section_provider.getEngine();

        if (!isAllowed(engine)) return false;

        // success story...
        section_provider.directCall(cmdline, stamp, getInternalPort());

        return true;
    }

    void kickWinPerf(const AnswerId Tp, const std::string& Ip);
    void kickPlugins(const AnswerId Tp, const std::string& Ip);

    template <typename T>
    std::string generate() {
        static_assert(std::is_base_of<cma::provider::Synchronous, T>::value,
                      "Must be Synchronous based");
        T section;
        section.updateSectionStatus();
        return section.generateContent();
    }

    // Answer must be build in specific order:
    // <pre sections[s]> - usually Check_MK
    // body from answer
    // <post sections[s]>- usually system time
    AnswerDataBlock wrapResultWithStaticSections(const AnswerDataBlock& block) {
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
        } catch (std::exception& e) {
            XLOG::l.crit(XLOG_FUNC + "Weird exception '{}'", e.what());
        }

        return result;
    }

    void logAnswerProcessing(bool success) {
        auto get_segments_text = [this]() -> std::string {
            auto list = answer_.segmentNameList();
            std::string s;
            for (auto const& l : list) {
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

    // We wait here for all answers from all providers, internal and external.
    // The call is *blocking*
    // #TODO break waiting
    cma::srv::AsyncAnswer::DataBlock getAnswer(int Count) {
        using namespace std::chrono;
        XLOG::t.i("waiting futures(only start)");
        int count = Count;

        int future_count = 0;
        auto p = steady_clock::now();

        // here we are starting futures, i.e. just fire all
        // futures in C++ kind of black magic, do not care too much
        for_each(vf_.begin(), vf_.end(),  // scan future array
                 [&future_count](std::future<bool>& x) {
                     // kill future
                     x.get();
                     ++future_count;
                 });

        auto p1 = steady_clock::now();
        XLOG::t.i("futures ready in {} milliseconds",
                  (int)duration_cast<milliseconds>(p1 - p).count());

        // set count of started to await for answer
        // count is from startProviders
        answer_.exeKickedCount(count);

        // now wait for answers
        auto success = answer_.waitAnswer(seconds(max_wait_time_));
        logAnswerProcessing(success);

        auto result = std::move(answer_.getDataAndClear());
        return wrapResultWithStaticSections(result);
    }

    // over simplified section provider
    class SectionProviderText {
    public:
        SectionProviderText(const std::string Name, const std::string Text)
            : name_(Name), text_(Text) {}

        std::future<bool> kick(const AnswerId Tp, ServiceProcessor* Proc) {
            return std::async(
                std::launch::async,
                [this](const AnswerId Tp, ServiceProcessor* Proc) {
                    auto block = gatherData();
                    if (block) {
                        XLOG::d("Provider '{}' added answer", name_);
                        return Proc->addSectionToAnswer(name_, Tp, *block);
                    } else {
                        XLOG::l("Provider '{}' FAILED answer", name_);
                        Proc->addSectionToAnswer(name_, Tp);
                        return false;
                    }
                },
                Tp,   // param 1
                Proc  // param 2

            );
        }

    private:
        std::string name_;
        std::string text_;
        std::optional<std::vector<uint8_t>> gatherData() {
            std::vector<uint8_t> v;
            v.assign(text_.begin(), text_.end());
            return v;
        }
    };

    class SectionProviderFile {
    public:
        SectionProviderFile(const std::string Name, const std::wstring FileName)
            : name_(Name), file_name_(FileName) {}

        std::future<bool> kick(const AnswerId Tp, ServiceProcessor* Proc) {
            return std::async(
                std::launch::async,
                [this](const AnswerId Tp, ServiceProcessor* Proc) {
                    auto block = gatherData();
                    xlog::l("Provider %s added answer", name_.c_str());
                    if (block)
                        return Proc->addSectionToAnswer(name_, Tp, *block);
                    else
                        return false;
                },
                Tp,   // param 1
                Proc  // param 2

            );
        }

    private:
        std::string name_;
        std::wstring file_name_;
        std::optional<std::vector<uint8_t>> gatherData() {
            auto f = cma::cfg::FindExeFileOnPath(file_name_);
            return cma::tools::ReadFileInVector(file_name_.c_str());
        }
    };

    // starting executable(any!) with valid command line
    // API to start exe
    std::future<bool> kickExe(
        bool Async,  // controlled from the config
        const std::wstring ExeName, const AnswerId Tp,
        ServiceProcessor* Proc,           // host
        const std::wstring& SegmentName,  // identifies exe
        int Timeout,                      // for exe
        const std::wstring& CommandLine) {
        return std::async(
            Async ? std::launch::async : std::launch::deferred,
            [this, ExeName](const AnswerId Tp, ServiceProcessor* Proc,
                            const std::wstring& SegmentName, int Timeout,
                            const std::wstring& CommandLine) {
                XLOG::l.i("Exec {} for {} started",
                          wtools::ConvertToUTF8(ExeName),
                          wtools::ConvertToUTF8(SegmentName));

                auto full_path = cma::cfg::FindExeFileOnPath(ExeName);
                if (full_path.empty()) {
                    std::string path_string = "";
                    auto paths = cma::cfg::GetExePaths();
                    for (const auto& dir : paths) {
                        path_string += dir.u8string() + "\n";
                    }
                    XLOG::l("File {} not found on the path {}",
                            wtools::ConvertToUTF8(ExeName), path_string);
                    return false;
                }

                // make command line
                auto port = wtools::ConvertToUTF16(Proc->getInternalPort());
                auto cmd_line =
                    fmt::format(L"\"{}\" -runonce {} {} id:{} timeout:{} {}",
                                full_path,    // exe
                                SegmentName,  // name of peer
                                port,         // port to communicate
                                Tp.time_since_epoch().count(),  // answer id
                                Timeout, CommandLine);

                XLOG::d.i("async RunStdCmd: {}",
                          wtools::ConvertToUTF8(cmd_line));
                cma::tools::RunStdCommand(cmd_line, false);

                return true;
            },
            Tp,           // param 1
            Proc,         // param 2
            SegmentName,  // section name
            Timeout, CommandLine

        );
    }

#if 0
    SectionProviderText txt_provider_{"Text", "<<<IAMSECTIONTOO>>>"};
    SectionProviderFile file_provider_{
        "File", L"test_files\\sections\\test_output.txt"};
#endif

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
    FRIEND_TEST(SectionProviderOhm, ConditionallyStartOhm);

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
