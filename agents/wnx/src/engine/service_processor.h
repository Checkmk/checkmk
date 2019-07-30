
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

bool SystemMailboxCallback(const cma::MailSlot* Slot, const void* Data, int Len,
                           void* Context);

class ServiceProcessor;

// wrapper to use section engine ASYNCHRONOUS by default
//
template <typename T>
class SectionProvider {
public:
    SectionProvider() : section_expected_timeout_(0) {
        provider_uniq_name_ = engine_.getUniqName();
    }

    // rarely used constructor, probably for tests only
    SectionProvider(const std::string UniqName,  // id for the provider
                    char Separator)
        : provider_uniq_name_(UniqName), engine_(UniqName, Separator) {
        provider_uniq_name_ = engine_.getUniqName();
    }

    // #TODO this function is not simple enough
    std::future<bool> kick(
        bool Async,                 // type of execution
        const std::string CmdLine,  // command line, first is Ip address
        const AnswerId Tp,          // expected id
        ServiceProcessor* Proc,     // hosting object
        const std::string SectionName =
            std::string(cma::section::kUseEmbeddedName)) {
        engine_.loadConfig();
        engine_.updateSectionStatus();
        section_expected_timeout_ = engine_.timeout();
        return std::async(
            Async ? std::launch::async : std::launch::deferred,
            [this](const std::string CommandLine,  //
                   const AnswerId Tp,              //
                   const ServiceProcessor* Proc,   //
                   const std::string SectionName) {
                engine_.registerCommandLine(CommandLine);
                auto port_name = Proc->getInternalPort();
                auto id = Tp.time_since_epoch().count();
                goGoGo(SectionName, CommandLine, port_name, id);
                XLOG::l.t("Provider '{}' started, id '{}' port [{}]",
                          provider_uniq_name_, id, port_name);

                return true;
            },
            CmdLine,     //
            Tp,          // param 1
            Proc,        // param 2
            SectionName  // section name

        );
    }

    const T& getEngine() const { return engine_; }
    T& getEngine() { return engine_; }

    int expectedTimeout() const { return section_expected_timeout_; }

protected:
    std::string provider_uniq_name_;
    T engine_;
    int section_expected_timeout_;

    void goGoGo(const std::string& SectionName,  //
                const std::string& CommandLine,  //
                const std::string& Port,         //
                uint64_t Marker) {               // std marker
        auto cmd_line =
            std::to_string(Marker) + " " + SectionName + " " + CommandLine;

        engine_.startSynchronous(Port, cmd_line);
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
    const std::string getInternalPort() const { return internal_port_; }
    const std::wstring getInternalPortWide() const {
        std::wstring port(internal_port_.begin(), internal_port_.end());
        return port;
    }

    // functions for testing/verifying
    void startTestingMainThread();
    void stopTestingMainThread();

    // called by callbacks from Internal Transport section providers
    bool addSectionToAnswer(const std::string& Name, const AnswerId Tp,
                            const AsyncAnswer::DataBlock& Data) {
        return answer_.addSegment(Name, Tp, Data);
    }

    // called when no data for section generated - this is ok
    bool addSectionToAnswer(const std::string& Name, const AnswerId Tp) {
        return answer_.addSegment(Name, Tp, std::vector<uint8_t>());
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

    // type of breaks in mainWaitLoop
    enum class Signal { restart, quit };

    // returns break type(what todo)
    Signal mainWaitLoop() {
        using namespace cma::cfg;
        XLOG::l.i("main Wait Loop");
        // memorize vars to check for changes in loop below
        auto ipv6 = groups::global.ipv6();
        auto port = groups::global.port();
        while (1) {
            using namespace std::chrono;

            // Perform main service function here...

            // special case when thread is one time run
            if (!callback_(static_cast<const void*>(this))) break;
            if (delay_ == 0ms) break;

            // check for config update and inform external port
            auto new_ipv6 = groups::global.ipv6();
            auto new_port = groups::global.port();
            if (new_ipv6 != ipv6 || new_port != port) {
                XLOG::l.i(
                    "Restarting server with new parameters [{}] ipv6:[{}]",
                    new_port, new_port);
                return Signal::restart;
            }

            // wait and check
            if (timedWaitForStop()) {
                XLOG::l.t("Stop request is set");
                break;  // signaled stop
            }
        }
        XLOG::l.t("main Wait Loop END");
        return Signal::quit;
    }

    AsyncAnswer answer_;  // queue in the future, now only one answer for all

    std::vector<std::future<bool>> vf_;

    // called from the network callbacks in ExternalPort
    std::optional<AnswerId> openAnswer(const std::string Ip) {
        // race condition below
        using namespace std::chrono;
        if (answer_.isAnswerInUse() &&
            !answer_.isAnswerOlder(30000ms))  // answer is in process
        {
            XLOG::l("Answer is in use and too young - to be fixed");
            return {};  // #TODO make async here
        }

        // answer may be reused
        answer_.dropAnswer();
        answer_.prepareAnswer(Ip);  // is temporary
        auto tp = answer_.getId();

        return tp;
    }

    //
    int startProviders(AnswerId Tp, std::string Ip);

    // all pre operation required for normal functionality
    void preStart();
    void detachedPluginsStart();

private:
    void preLoadConfig();
    TheMiniProcess ohm_process_;
    int max_timeout_;  // this is waiting time for all section to run
    template <typename T>
    bool tryToKick(T& SecProv, AnswerId Tp, const std::string& Ip) {
        const auto& engine = SecProv.getEngine();

        // check time
        auto allowed_by_time = engine.isAllowedByTime();
        if (!allowed_by_time) {
            XLOG::t("Skipping '{}' by time", engine.getUniqName());
            return false;
        }

        // check config
        auto allowed = engine.isAllowedByCurrentConfig();
        if (!allowed) {
            XLOG::t("Skipping '{}' by config", engine.getUniqName());
            return false;
        }

        // success story...
        vf_.emplace_back(SecProv.kick(true, Ip, Tp, this));
        auto expected_timeout = SecProv.expectedTimeout();
        if (expected_timeout > 0) {
            max_timeout_ = std::max(expected_timeout, max_timeout_);
            XLOG::t.i("Max Timeout set to '{}'", max_timeout_);
        }

        return true;
    }

    void kickWinPerf(const AnswerId Tp, const std::string& Ip);
    void kickPlugins(const AnswerId Tp, const std::string& Ip);

    // Answer must be build in specific order:
    // <pre sections[s]> - usually Check_MK
    // body from answer
    // <post sections[s]>- usually system time
    AnswerDataBlock wrapResultWithStaticSections(const AnswerDataBlock& Block) {
        // pre sections generation
        provider::CheckMk check_mk;
        check_mk.updateSectionStatus();
        auto pre = check_mk.generateContent(section::kUseEmbeddedName);

        // post sections generation
        provider::SystemTime system_time;
        system_time.updateSectionStatus();
        auto post = system_time.generateContent(section::kUseEmbeddedName);

        // concatenating
        AnswerDataBlock result;
        try {
            result.reserve(pre.size() + Block.size() + post.size());

            result.insert(result.end(), pre.begin(), pre.end());
            result.insert(result.end(), Block.begin(), Block.end());
            result.insert(result.end(), post.begin(), post.end());
        } catch (std::exception& e) {
            XLOG::l.crit(XLOG_FUNC + "Weird exception {}", e.what());
        }

        return result;
    }

    // We wait here for all answers from all providers, internal and external.
    // The call is *blocking*
    // #TODO gtest
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
        if (!answer_.waitAnswer(std::chrono::seconds(max_timeout_))) {
            XLOG::l(XLOG_FLINE + " no full answer: awaited [{}], received [{}]",
                    answer_.awaitingSegments(),   // expected count
                    answer_.receivedSegments());  // on the hand
        }

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

                auto cmd_line = fmt::format(
                    L"\"{}\" -runonce {} {} id:{} timeout:{} {}",
                    full_path,                      // exe
                    SegmentName,                    // name of peer
                    Proc->getInternalPortWide(),    // port to communicate
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
    SectionProvider<provider::Uptime> uptime_provider_;
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
    friend class ServiceControllerTest;
    FRIEND_TEST(ServiceControllerTest, StartStopExe);
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
