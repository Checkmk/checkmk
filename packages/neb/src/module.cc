// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Needed for S_ISSOCK
// NOLINTNEXTLINE(bugprone-reserved-identifier,cert-dcl37-c,cert-dcl51-cpp,cppcoreguidelines-macro-usage)
#define _XOPEN_SOURCE 500

#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <charconv>
#include <chrono>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <exception>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <map>
#include <memory>
#include <optional>
#include <ranges>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include "livestatus/Average.h"
#include "livestatus/ChronoUtils.h"
#include "livestatus/InputBuffer.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/Poller.h"
#include "livestatus/Queue.h"
#include "livestatus/RegExp.h"
#include "livestatus/StringUtils.h"
#include "livestatus/TrialManager.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
#include "livestatus/data_encoding.h"
#include "livestatus/global_counters.h"
#include "neb/CmkVersion.h"
#include "neb/Comment.h"
#include "neb/Downtime.h"
#include "neb/NebCore.h"
#include "neb/TimeperiodsCache.h"
#include "neb/nagios.h"

using namespace std::chrono_literals;
using namespace std::string_literals;
using namespace std::string_view_literals;

// NOLINTBEGIN(cppcoreguidelines-avoid-non-const-global-variables)
// TODO(sp) Globals are accessed in NebCore/TimeperiodsCache without any header.
// NOLINTBEGIN(misc-use-internal-linkage)
NEB_API_VERSION(CURRENT_NEB_API_VERSION)

size_t g_livestatus_threads = 10;
int g_num_queued_connections = 0;
std::atomic_int32_t g_livestatus_active_connections{0};
TimeperiodsCache *g_timeperiods_cache = nullptr;
// simple statistics data for TableStatus
int g_num_hosts;
int g_num_services;
bool g_any_event_handler_enabled;
double g_average_active_latency;
Average g_avg_livestatus_usage;  // NOLINT(cert-err58-cpp)
// NOLINTEND(misc-use-internal-linkage)

namespace {
std::chrono::milliseconds fl_idle_timeout = 5min;  // NOLINT(cert-err58-cpp)

std::chrono::milliseconds fl_query_timeout = 10s;  // NOLINT(cert-err58-cpp)

size_t fl_thread_stack_size = size_t{1024} * 1024;

void *fl_nagios_handle;
int fl_unix_socket = -1;
int fl_max_fd_ever = 0;

NagiosPathConfig fl_paths;

std::string fl_edition{"free"};  // NOLINT(cert-err58-cpp)

bool fl_should_terminate;

struct ThreadInfo {
    pthread_t id{};
    std::string name;
};

std::vector<ThreadInfo> fl_thread_info;
thread_local ThreadInfo *tl_info;

NagiosLimits fl_limits;

int fl_thread_running = 0;

NagiosAuthorization fl_authorization;

Encoding fl_data_encoding{Encoding::utf8};

Logger *fl_logger_nagios = nullptr;
LogLevel fl_livestatus_log_level = LogLevel::notice;
using ClientQueue_t = Queue<int>;
ClientQueue_t *fl_client_queue = nullptr;

std::map<unsigned long, std::unique_ptr<Downtime>> fl_downtimes;

std::map<unsigned long, std::unique_ptr<Comment>> fl_comments;

NebCore *fl_core = nullptr;
// NOLINTEND(cppcoreguidelines-avoid-non-const-global-variables)

void update_status() {
    bool any_event_handler_enabled{false};
    double active_latency{0};
    int num_active_checks{0};

    int num_hosts = 0;
    for (const host *h = host_list; h != nullptr; h = h->next) {
        num_hosts++;
        any_event_handler_enabled =
            any_event_handler_enabled || (h->event_handler_enabled > 0);
        if (h->check_type == HOST_CHECK_ACTIVE) {
            num_active_checks++;
            active_latency += h->latency;
        }
    }

    int num_services = 0;
    for (const service *s = service_list; s != nullptr; s = s->next) {
        num_services++;
        any_event_handler_enabled =
            any_event_handler_enabled || (s->event_handler_enabled > 0);
        if (s->check_type == SERVICE_CHECK_ACTIVE) {
            num_active_checks++;
            active_latency += s->latency;
        }
    }

    // batch all the global updates
    g_num_hosts = num_hosts;
    g_num_services = num_services;
    g_any_event_handler_enabled = any_event_handler_enabled;
    g_average_active_latency = active_latency / std::max(num_active_checks, 1);
    g_avg_livestatus_usage.update(
        static_cast<double>(g_livestatus_active_connections) /
        static_cast<double>(g_livestatus_threads));
}

bool shouldTerminate() { return fl_should_terminate; }
void shouldTerminate(bool value) { fl_should_terminate = value; }

void livestatus_count_fork() { counterIncrement(Counter::forks); }

void livestatus_cleanup_after_fork() {
    // 4.2.2010: Deactivate the cleanup function. It might cause
    // more trouble than it tries to avoid. It might lead to a deadlock
    // with Nagios' fork()-mechanism...
    // store_deinit();
    struct stat st{};

    // We need to close our server and client sockets. Otherwise
    // our connections are inherited to host and service checks.
    // If we close our client connection in such a situation,
    // the connection will still be open since and the client will
    // hang while trying to read further data. And the CLOEXEC is
    // not atomic :-(

    // Eventuell sollte man hier anstelle von store_deinit() nicht
    // darauf verlassen, dass die fl_client_queue alle Verbindungen zumacht.
    // Es sind ja auch Dateideskriptoren offen, die von Threads gehalten
    // werden und nicht mehr in der Queue sind. Und in store_deinit()
    // wird mit mutexes rumgemacht....
    for (int i = 3; i < fl_max_fd_ever; i++) {
        if (0 == fstat(i, &st) && S_ISSOCK(st.st_mode)) {
            ::close(i);
        }
    }
}

void *main_thread(void *data) {
    tl_info = static_cast<ThreadInfo *>(data);
    auto *logger = fl_core->loggerLivestatus();
    auto last_update_status = std::chrono::system_clock::now();
    while (!shouldTerminate()) {
        do_statistics();
        auto now = std::chrono::system_clock::now();
        if (now - last_update_status >= 5s) {
            update_status();
            last_update_status = now;
        }
        if (!Poller{}.wait(2500ms, fl_unix_socket, PollEvents::in, logger)) {
            if (errno == ETIMEDOUT) {
                continue;
            }
            break;
        }
        const int cc =
            ::accept4(fl_unix_socket, nullptr, nullptr, SOCK_CLOEXEC);
        if (cc == -1) {
            const generic_error ge("cannot accept client connection");
            Warning(logger) << ge;
            continue;
        }
        fl_max_fd_ever = std::max(cc, fl_max_fd_ever);
        auto &&[ok, size] =
            fl_client_queue->push(cc, queue_overflow_strategy::pop_oldest);
        switch (ok) {
            case queue_status::overflow:
            case queue_status::joinable: {
                const generic_error ge("cannot enqueue client socket");
                Warning(logger) << ge;
                break;
            }
            case queue_status::ok:
                break;
        }
        g_num_queued_connections++;
        counterIncrement(Counter::connections);
    }
    Notice(logger) << "socket thread has terminated";
    return nullptr;
}

void *client_thread(void *data) {
    tl_info = static_cast<ThreadInfo *>(data);
    auto *logger = fl_core->loggerLivestatus();
    while (!shouldTerminate()) {
        if (auto &&elem =
                fl_client_queue->pop(queue_pop_strategy::blocking, {})) {
            auto &&[fd, size] = *elem;
            g_num_queued_connections--;
            g_livestatus_active_connections++;
            Debug(logger) << "accepted client connection on fd " << fd;
            InputBuffer input_buffer{fd, [] { return shouldTerminate(); },
                                     logger, fl_query_timeout, fl_idle_timeout};
            bool keepalive = true;
            unsigned requestnr = 0;
            while (keepalive && !shouldTerminate()) {
                if (++requestnr > 1) {
                    Debug(logger) << "handling request " << requestnr
                                  << " on same connection";
                }
                counterIncrement(Counter::requests);
                OutputBuffer output_buffer{fd, [] { return shouldTerminate(); },
                                           logger};
                keepalive = fl_core->answerRequest(input_buffer, output_buffer);
            }
            ::close(fd);
        }
        g_livestatus_active_connections--;
    }
    return nullptr;
}

class NagiosHandler : public Handler {
public:
    NagiosHandler() { setFormatter(std::make_unique<NagiosFormatter>()); }

private:
    class NagiosFormatter : public Formatter {
        void format(std::ostream &os, const LogRecord &record) override {
            os << "livestatus: " << record.getMessage();
        }
    };

    void publish(const LogRecord &record) override {
        std::ostringstream os;
        getFormatter()->format(os, record);
        write_to_all_logs_(os);
    }
};

class LivestatusHandler : public FileHandler {
public:
    explicit LivestatusHandler(const std::string &filename)
        : FileHandler(filename) {
        setFormatter(std::make_unique<LivestatusFormatter>());
    }

private:
    class LivestatusFormatter : public Formatter {
        void format(std::ostream &os, const LogRecord &record) override {
            os << FormattedTimePoint(record.getTimePoint()) << " ["
               << tl_info->name << "] " << record.getMessage();
        }
    };
};

std::string_view callback_name(int callback_type) {
    static constexpr std::array<std::pair<int, std::string_view>, 33> table{{
        {NEBCALLBACK_RESERVED0, "RESERVED0"sv},
        {NEBCALLBACK_RESERVED1, "RESERVED1"sv},
        {NEBCALLBACK_RESERVED2, "RESERVED2"sv},
        {NEBCALLBACK_RESERVED3, "RESERVED3"sv},
        {NEBCALLBACK_RESERVED4, "RESERVED4"sv},
        {NEBCALLBACK_RAW_DATA, "RAW"sv},
        {NEBCALLBACK_NEB_DATA, "NEB"sv},
        {NEBCALLBACK_PROCESS_DATA, "PROCESS"sv},
        {NEBCALLBACK_TIMED_EVENT_DATA, "TIMED_EVENT"sv},
        {NEBCALLBACK_LOG_DATA, "LOG"sv},
        {NEBCALLBACK_SYSTEM_COMMAND_DATA, "SYSTEM_COMMAND"sv},
        {NEBCALLBACK_EVENT_HANDLER_DATA, "EVENT_HANDLER"sv},
        {NEBCALLBACK_NOTIFICATION_DATA, "NOTIFICATION"sv},
        {NEBCALLBACK_SERVICE_CHECK_DATA, "SERVICE_CHECK"sv},
        {NEBCALLBACK_HOST_CHECK_DATA, "HOST_CHECK"sv},
        {NEBCALLBACK_COMMENT_DATA, "COMMENT"sv},
        {NEBCALLBACK_DOWNTIME_DATA, "DOWNTIME"sv},
        {NEBCALLBACK_FLAPPING_DATA, "FLAPPING"sv},
        {NEBCALLBACK_PROGRAM_STATUS_DATA, "PROGRAM_STATUS"sv},
        {NEBCALLBACK_HOST_STATUS_DATA, "HOST_STATUS"sv},
        {NEBCALLBACK_SERVICE_STATUS_DATA, "SERVICE_STATUS"sv},
        {NEBCALLBACK_ADAPTIVE_PROGRAM_DATA, "ADAPTIVE_PROGRAM"sv},
        {NEBCALLBACK_ADAPTIVE_HOST_DATA, "ADAPTIVE_HOST"sv},
        {NEBCALLBACK_ADAPTIVE_SERVICE_DATA, "ADAPTIVE_SERVICE"sv},
        {NEBCALLBACK_EXTERNAL_COMMAND_DATA, "EXTERNAL_COMMAND"sv},
        {NEBCALLBACK_AGGREGATED_STATUS_DATA, "AGGREGATED_STATUS"sv},
        {NEBCALLBACK_RETENTION_DATA, "RETENTION"sv},
        {NEBCALLBACK_CONTACT_NOTIFICATION_DATA, "CONTACT_NOTIFICATION"sv},
        {NEBCALLBACK_CONTACT_NOTIFICATION_METHOD_DATA,
         "CONTACT_NOTIFICATION_METHOD"sv},
        {NEBCALLBACK_ACKNOWLEDGEMENT_DATA, "ACKNOWLEDGEMENT"sv},
        {NEBCALLBACK_STATE_CHANGE_DATA, "STATE_CHANGE"sv},
        {NEBCALLBACK_CONTACT_STATUS_DATA, "CONTACT_STATUS"sv},
        {NEBCALLBACK_ADAPTIVE_CONTACT_DATA, "ADAPTIVE_CONTACT"sv},
    }};
    const auto *it = std::ranges::find_if(
        table, [&](const auto &entry) { return entry.first == callback_type; });
    return it == end(table) ? "UNKNOWN"sv : it->second;
}

std::string_view data_type_name(int type) {
    static constexpr std::array<std::pair<int, std::string_view>, 71> table{{
        {NEBTYPE_NONE, "NONE"sv},
        //
        {NEBTYPE_HELLO, "HELLO"sv},
        {NEBTYPE_GOODBYE, "GOODBYE"sv},
        {NEBTYPE_INFO, "INFO"sv},
        //
        {NEBTYPE_PROCESS_START, "PROCESS_START"sv},
        {NEBTYPE_PROCESS_DAEMONIZE, "PROCESS_DAEMONIZE"sv},
        {NEBTYPE_PROCESS_RESTART, "PROCESS_RESTART"sv},
        {NEBTYPE_PROCESS_SHUTDOWN, "PROCESS_SHUTDOWN"sv},
        {NEBTYPE_PROCESS_PRELAUNCH, "PROCESS_PRELAUNCH"sv},
        {NEBTYPE_PROCESS_EVENTLOOPSTART, "PROCESS_EVENTLOOPSTART"sv},
        {NEBTYPE_PROCESS_EVENTLOOPEND, "PROCESS_EVENTLOOPEND"sv},
        //
        {NEBTYPE_TIMEDEVENT_ADD, "TIMEDEVENT_ADD"sv},
        {NEBTYPE_TIMEDEVENT_REMOVE, "TIMEDEVENT_REMOVE"sv},
        {NEBTYPE_TIMEDEVENT_EXECUTE, "TIMEDEVENT_EXECUTE"sv},
        {NEBTYPE_TIMEDEVENT_DELAY, "TIMEDEVENT_DELAY"sv},
        {NEBTYPE_TIMEDEVENT_SKIP, "TIMEDEVENT_SKIP"sv},
        {NEBTYPE_TIMEDEVENT_SLEEP, "TIMEDEVENT_SLEEP"sv},
        //
        {NEBTYPE_LOG_DATA, "LOG_DATA"sv},
        {NEBTYPE_LOG_ROTATION, "LOG_ROTATION"sv},
        //
        {NEBTYPE_SYSTEM_COMMAND_START, "SYSTEM_COMMAND_START"sv},
        {NEBTYPE_SYSTEM_COMMAND_END, "SYSTEM_COMMAND_END"sv},
        //
        {NEBTYPE_EVENTHANDLER_START, "EVENTHANDLER_START"sv},
        {NEBTYPE_EVENTHANDLER_END, "EVENTHANDLER_END"sv},
        //
        {NEBTYPE_NOTIFICATION_START, "NOTIFICATION_START"sv},
        {NEBTYPE_NOTIFICATION_END, "NOTIFICATION_END"sv},
        {NEBTYPE_CONTACTNOTIFICATION_START, "CONTACTNOTIFICATION_START"sv},
        {NEBTYPE_CONTACTNOTIFICATION_END, "CONTACTNOTIFICATION_END"sv},
        {NEBTYPE_CONTACTNOTIFICATIONMETHOD_START,
         "CONTACTNOTIFICATIONMETHOD_START"sv},
        {NEBTYPE_CONTACTNOTIFICATIONMETHOD_END,
         "CONTACTNOTIFICATIONMETHOD_END"sv},
        //
        {NEBTYPE_SERVICECHECK_INITIATE, "SERVICECHECK_INITIATE"sv},
        {NEBTYPE_SERVICECHECK_PROCESSED, "SERVICECHECK_PROCESSED"sv},
        {NEBTYPE_SERVICECHECK_RAW_START, "SERVICECHECK_RAW_START"sv},
        {NEBTYPE_SERVICECHECK_RAW_END, "SERVICECHECK_RAW_END"sv},
        {NEBTYPE_SERVICECHECK_ASYNC_PRECHECK, "SERVICECHECK_ASYNC_PRECHECK"sv},
        //
        {NEBTYPE_HOSTCHECK_INITIATE, "HOSTCHECK_INITIATE"sv},
        {NEBTYPE_HOSTCHECK_PROCESSED, "HOSTCHECK_PROCESSED"sv},
        {NEBTYPE_HOSTCHECK_RAW_START, "HOSTCHECK_RAW_START"sv},
        {NEBTYPE_HOSTCHECK_RAW_END, "HOSTCHECK_RAW_END"sv},
        {NEBTYPE_HOSTCHECK_ASYNC_PRECHECK, "HOSTCHECK_ASYNC_PRECHECK"sv},
        {NEBTYPE_HOSTCHECK_SYNC_PRECHECK, "HOSTCHECK_SYNC_PRECHECK"sv},
        //
        {NEBTYPE_COMMENT_ADD, "COMMENT_ADD"sv},
        {NEBTYPE_COMMENT_DELETE, "COMMENT_DELETE"sv},
        {NEBTYPE_COMMENT_LOAD, "COMMENT_LOAD"sv},
        //
        {NEBTYPE_FLAPPING_START, "FLAPPING_START"sv},
        {NEBTYPE_FLAPPING_STOP, "FLAPPING_STOP"sv},
        //
        {NEBTYPE_DOWNTIME_ADD, "DOWNTIME_ADD"sv},
        {NEBTYPE_DOWNTIME_DELETE, "DOWNTIME_DELETE"sv},
        {NEBTYPE_DOWNTIME_LOAD, "DOWNTIME_LOAD"sv},
        {NEBTYPE_DOWNTIME_START, "DOWNTIME_START"sv},
        {NEBTYPE_DOWNTIME_STOP, "DOWNTIME_STOP"sv},
        //
        {NEBTYPE_PROGRAMSTATUS_UPDATE, "PROGRAMSTATUS_UPDATE"sv},
        {NEBTYPE_HOSTSTATUS_UPDATE, "HOSTSTATUS_UPDATE"sv},
        {NEBTYPE_SERVICESTATUS_UPDATE, "SERVICESTATUS_UPDATE"sv},
        {NEBTYPE_CONTACTSTATUS_UPDATE, "CONTACTSTATUS_UPDATE"sv},
        //
        {NEBTYPE_ADAPTIVEPROGRAM_UPDATE, "ADAPTIVEPROGRAM_UPDATE"sv},
        {NEBTYPE_ADAPTIVEHOST_UPDATE, "ADAPTIVEHOST_UPDATE"sv},
        {NEBTYPE_ADAPTIVESERVICE_UPDATE, "ADAPTIVESERVICE_UPDATE"sv},
        {NEBTYPE_ADAPTIVECONTACT_UPDATE, "ADAPTIVECONTACT_UPDATE"sv},

        {NEBTYPE_EXTERNALCOMMAND_START, "EXTERNALCOMMAND_START"sv},
        {NEBTYPE_EXTERNALCOMMAND_END, "EXTERNALCOMMAND_END"sv},
        //
        {NEBTYPE_AGGREGATEDSTATUS_STARTDUMP, "AGGREGATEDSTATUS_STARTDUMP"sv},
        {NEBTYPE_AGGREGATEDSTATUS_ENDDUMP, "AGGREGATEDSTATUS_ENDDUMP"sv},
        //
        {NEBTYPE_RETENTIONDATA_STARTLOAD, "RETENTIONDATA_STARTLOAD"sv},
        {NEBTYPE_RETENTIONDATA_ENDLOAD, "RETENTIONDATA_ENDLOAD"sv},
        {NEBTYPE_RETENTIONDATA_STARTSAVE, "RETENTIONDATA_STARTSAVE"sv},
        {NEBTYPE_RETENTIONDATA_ENDSAVE, "RETENTIONDATA_ENDSAVE"sv},
        //
        {NEBTYPE_ACKNOWLEDGEMENT_ADD, "ACKNOWLEDGEMENT_ADD"sv},
        {NEBTYPE_ACKNOWLEDGEMENT_REMOVE, "ACKNOWLEDGEMENT_REMOVE"sv},
        {NEBTYPE_ACKNOWLEDGEMENT_LOAD, "ACKNOWLEDGEMENT_LOAD"sv},
        //
        {NEBTYPE_STATECHANGE_START, "STATECHANGE_START"sv},
        {NEBTYPE_STATECHANGE_END, "STATECHANGE_END"sv},
    }};
    const auto *it = std::ranges::find_if(
        table, [&](const auto &entry) { return entry.first == type; });
    return it == end(table) ? "UNKNOWN"sv : it->second;
}

void log_callback(int callback_type, int type) {
    // TODO(sp) This is quite a hack because we get callbacks *very* early and
    // our loggers have not been set up then.
    if (fl_livestatus_log_level == LogLevel::debug) {
        std::ofstream{fl_paths.log_file, std::ios::app}
            << FormattedTimePoint(std::chrono::system_clock::now())
            << " [nagios] " << callback_name(callback_type)
            << " callback: " << data_type_name(type) << "\n";
    }
}

void start_threads() {
    if (fl_thread_running == 1) {
        return;
    }

    shouldTerminate(false);
    auto *logger = fl_core->loggerLivestatus();
    logger->setLevel(fl_livestatus_log_level);
    logger->setUseParentHandlers(false);
    try {
        logger->setHandler(
            std::make_unique<LivestatusHandler>(fl_paths.log_file));
    } catch (const generic_error &ex) {
        Warning(fl_logger_nagios) << ex;
    }

    update_status();
    Informational(fl_logger_nagios)
        << "starting main thread and " << g_livestatus_threads
        << " client threads";

    if (auto result = pthread_atfork(livestatus_count_fork, nullptr,
                                     livestatus_cleanup_after_fork);
        result != 0) {
        Warning(fl_logger_nagios)
            << generic_error{result, "cannot set fork handler"};
    }

    pthread_attr_t attr;
    if (auto result = pthread_attr_init(&attr); result != 0) {
        Warning(fl_logger_nagios) << generic_error{
            result, "cannot create livestatus thread attributes"};
    }
    size_t defsize = 0;
    if (auto result = pthread_attr_getstacksize(&attr, &defsize); result != 0) {
        Warning(fl_logger_nagios) << generic_error{
            result, "cannot get default livestatus thread stack size"};
    } else {
        Debug(fl_logger_nagios) << "default stack size is " << defsize;
    }
    if (auto result = pthread_attr_setstacksize(&attr, fl_thread_stack_size);
        result != 0) {
        Warning(fl_logger_nagios) << generic_error{
            result, "cannot set livestatus thread stack size to " +
                        std::to_string(fl_thread_stack_size)};
    } else {
        Debug(fl_logger_nagios)
            << "setting thread stack size to " << fl_thread_stack_size;
    }

    fl_thread_info.resize(g_livestatus_threads + 1);
    for (auto &info : fl_thread_info) {
        ptrdiff_t const idx = &info - fl_thread_info.data();
        if (idx == 0) {
            // start thread that listens on socket
            info.name = "main";
            if (auto result =
                    pthread_create(&info.id, nullptr, main_thread, &info);
                result != 0) {
                Warning(fl_logger_nagios)
                    << generic_error{result, "cannot create main thread"};
            }
            // Our current thread (i.e. the main one, confusing terminology)
            // needs thread-local infos for logging, too.
            tl_info = &info;
        } else {
            info.name = "client " + std::to_string(idx);
            if (auto result =
                    pthread_create(&info.id, &attr, client_thread, &info);
                result != 0) {
                Warning(fl_logger_nagios)
                    << generic_error{result, "cannot create livestatus thread"};
            }
        }
    }

    fl_core->dump_infos();
    fl_thread_running = 1;
    if (auto result = pthread_attr_destroy(&attr); result != 0) {
        Warning(fl_logger_nagios) << generic_error{
            result, "cannot destroy livestatus thread attributes"};
    }
}

void terminate_threads() {
    if (fl_thread_running != 0) {
        shouldTerminate(true);
        Informational(fl_logger_nagios) << "waiting for main to terminate...";
        if (auto result = pthread_join(fl_thread_info[0].id, nullptr);
            result != 0) {
            Warning(fl_logger_nagios) << generic_error{
                result, "cannot join thread " + fl_thread_info[0].name};
        }
        Informational(fl_logger_nagios)
            << "waiting for client threads to terminate...";
        fl_client_queue->join();
        while (auto &&elem =
                   fl_client_queue->pop(queue_pop_strategy::nonblocking, {})) {
            auto &&[fd, size] = *elem;
            ::close(fd);
        }
        for (const auto &info : fl_thread_info) {
            if (auto result = pthread_join(info.id, nullptr); result != 0) {
                Warning(fl_logger_nagios)
                    << generic_error{result, "cannot join thread " + info.name};
            }
        }
        Informational(fl_logger_nagios)
            << "main thread + " << g_livestatus_threads
            << " client threads have finished";
        fl_thread_running = 0;
        shouldTerminate(false);
    }
}

void open_unix_socket() {
    struct stat st{};
    if (stat(fl_paths.livestatus_socket.c_str(), &st) == 0) {
        if (::unlink(fl_paths.livestatus_socket.c_str()) == 0) {
            Debug(fl_logger_nagios)
                << "removed old socket file " << fl_paths.livestatus_socket;
        } else {
            throw generic_error{"cannot remove old socket file \"" +
                                fl_paths.livestatus_socket.string() + "\""};
        }
    }

    fl_unix_socket = ::socket(PF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    fl_max_fd_ever = fl_unix_socket;
    if (fl_unix_socket < 0) {
        throw generic_error{"cannot create UNIX socket"};
    }

    // Bind it to its address. This creates the file with the name
    // fl_paths.livestatus_socket
    struct sockaddr_un sockaddr{.sun_family = AF_UNIX, .sun_path = ""};
    fl_paths.livestatus_socket.string().copy(&sockaddr.sun_path[0],
                                             sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::bind(fl_unix_socket, reinterpret_cast<struct sockaddr *>(&sockaddr),
               sizeof(sockaddr)) < 0) {
        generic_error ge{"cannot bind UNIX socket to address \"" +
                         fl_paths.livestatus_socket.string() + "\""};
        ::close(fl_unix_socket);
        throw std::move(ge);
    }

    // Make writable group members (fchmod didn't do nothing for me. Don't
    // know why!)
    if (0 != ::chmod(fl_paths.livestatus_socket.c_str(), 0660)) {
        generic_error ge{
            "cannot change file permissions for UNIX socket at \"" +
            fl_paths.livestatus_socket.string() + "\" to 0660"};
        ::close(fl_unix_socket);
        throw std::move(ge);
    }

    if (0 != ::listen(fl_unix_socket, 3 /* backlog */)) {
        generic_error ge{"cannot listen to UNIX socket at \"" +
                         fl_paths.livestatus_socket.string() + "\""};
        ::close(fl_unix_socket);
        throw std::move(ge);
    }

    Informational(fl_logger_nagios)
        << "opened UNIX socket at " << fl_paths.livestatus_socket;
}

void close_unix_socket() {
    ::unlink(fl_paths.livestatus_socket.c_str());
    if (fl_unix_socket >= 0) {
        ::close(fl_unix_socket);
        fl_unix_socket = -1;
    }
}

int broker_host_check(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_host_check_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_HOSTCHECK_INITIATE:
        case NEBTYPE_HOSTCHECK_ASYNC_PRECHECK:
        case NEBTYPE_HOSTCHECK_SYNC_PRECHECK:
        case NEBTYPE_HOSTCHECK_RAW_START:
        case NEBTYPE_HOSTCHECK_RAW_END:
            break;
        case NEBTYPE_HOSTCHECK_PROCESSED:
            counterIncrement(Counter::host_checks);
            fl_core->triggers().notify_all(Triggers::Kind::check);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_service_check(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_service_check_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_SERVICECHECK_INITIATE:
        case NEBTYPE_SERVICECHECK_ASYNC_PRECHECK:
        case NEBTYPE_SERVICECHECK_RAW_START:
        case NEBTYPE_SERVICECHECK_RAW_END:
            break;
        case NEBTYPE_SERVICECHECK_PROCESSED:
            counterIncrement(Counter::service_checks);
            fl_core->triggers().notify_all(Triggers::Kind::check);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_comment(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_comment_data *>(data);
    log_callback(callback_type, info->type);
    const unsigned long id = info->comment_id;
    switch (info->type) {
        case NEBTYPE_COMMENT_ADD:
            // We get a NEBTYPE_COMMENT_LOAD *and* a NEBTYPE_COMMENT_ADD for a
            // single ADD_*_COMMENT command. The LOAD/DELETE events correspond
            // to the actual changes in the Nagios data structures, so we use
            // those and ignore the ADD.
            break;
        case NEBTYPE_COMMENT_LOAD: {
            auto *hst = ::find_host(info->host_name);
            auto *svc = info->service_description == nullptr
                            ? nullptr
                            : ::find_service(info->host_name,
                                             info->service_description);
            fl_comments[id] = std::make_unique<Comment>(Comment{
                ._id = info->comment_id,
                ._author = info->author_name,
                ._comment = info->comment_data,
                ._entry_type = static_cast<CommentType>(
                    static_cast<int32_t>(info->entry_type)),
                ._entry_time =
                    std::chrono::system_clock::from_time_t(info->entry_time),
                ._is_service = info->service_description != nullptr,
                ._host = hst,
                ._service = svc,
                ._expire_time =
                    std::chrono::system_clock::from_time_t(info->expire_time),
                ._persistent = info->persistent != 0,
                ._source = static_cast<CommentSource>(
                    static_cast<int32_t>(info->source)),
                ._expires = info->expires != 0});
            fl_core->triggers().notify_all(Triggers::Kind::comment);
            break;
        }
        case NEBTYPE_COMMENT_DELETE:
            if (fl_comments.erase(id) == 0) {
                Informational(fl_logger_nagios)
                    << "cannot delete non-existing comment " << id;
            }
            fl_core->triggers().notify_all(Triggers::Kind::comment);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_downtime(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_downtime_data *>(data);
    log_callback(callback_type, info->type);
    const unsigned long id = info->downtime_id;
    switch (info->type) {
        case NEBTYPE_DOWNTIME_ADD:
            // We get a NEBTYPE_DOWNTIME_LOAD *and* a NEBTYPE_DOWNTIME_ADD for a
            // single ADD_*_DOWNTIME command. The LOAD/DELETE events correspond
            // to the actual changes in the Nagios data structures, so we use
            // those and ignore the ADD. Note that Nagios adds a comment to the
            // host/service after the ADD, too, so we get additional callbacks.
            break;
        case NEBTYPE_DOWNTIME_LOAD: {
            auto *hst = ::find_host(info->host_name);
            auto *svc = info->service_description == nullptr
                            ? nullptr
                            : ::find_service(info->host_name,
                                             info->service_description);
            fl_downtimes[id] = std::make_unique<Downtime>(Downtime{
                ._id = static_cast<int32_t>(info->downtime_id),
                ._author = info->author_name,
                ._comment = info->comment_data,
                ._origin_is_rule = false,
                ._entry_time =
                    std::chrono::system_clock::from_time_t(info->entry_time),
                ._start_time =
                    std::chrono::system_clock::from_time_t(info->start_time),
                ._end_time =
                    std::chrono::system_clock::from_time_t(info->end_time),
                ._fixed = info->fixed != 0,
                ._duration = std::chrono::seconds{info->duration},
                ._host = hst,
                ._service = svc,
                ._triggered_by = static_cast<int32_t>(info->triggered_by),
                ._is_active = false,  // TODO(sp) initial state?
            });
            fl_core->triggers().notify_all(Triggers::Kind::downtime);
            break;
        }
        case NEBTYPE_DOWNTIME_DELETE:
            if (fl_downtimes.erase(id) == 0) {
                Informational(fl_logger_nagios)
                    << "cannot delete non-existing downtime " << id;
            }
            fl_core->triggers().notify_all(Triggers::Kind::downtime);
            break;
        case NEBTYPE_DOWNTIME_START:
            if (auto it = fl_downtimes.find(id); it != fl_downtimes.end()) {
                it->second->_is_active = true;
            }
            fl_core->triggers().notify_all(Triggers::Kind::downtime);
            break;

        case NEBTYPE_DOWNTIME_STOP:
            if (auto it = fl_downtimes.find(id); it != fl_downtimes.end()) {
                it->second->_is_active = false;
            }
            fl_core->triggers().notify_all(Triggers::Kind::downtime);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

void livestatus_log_alerts() {
    for (const ::host *hst = host_list; hst != nullptr; hst = hst->next) {
        if (hst->scheduled_downtime_depth > 0) {
            std::ostringstream os;
            os << "HOST DOWNTIME ALERT: " << hst->name
               << ";STARTED; Host has entered a period of scheduled downtime";
            write_to_all_logs_(os);
        }
    }
    for (const ::service *svc = service_list; svc != nullptr; svc = svc->next) {
        if (svc->scheduled_downtime_depth > 0) {
            std::ostringstream os;
            os << "SERVICE DOWNTIME ALERT: " << svc->host_name << ";"
               << svc->description
               << ";STARTED; Service has entered a period of scheduled downtime";
            write_to_all_logs_(os);
        }
    }
}

void log_initial_states() {
    livestatus_log_alerts();
    g_timeperiods_cache->logCurrentTimeperiods();
    write_to_all_logs_("logging initial states");
}

int broker_log(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_log_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_LOG_DATA:
            if (std::string_view{info->data}.starts_with("LOG ROTATION: "sv)) {
                log_initial_states();
            }
            // Note that we are called *after* the entry has been written to the
            // Nagios log file.
            counterIncrement(Counter::log_messages);
            // NOTE: We use logging very early, even before the core is
            // instantiated!
            if (fl_core != nullptr) {
                fl_core->triggers().notify_all(Triggers::Kind::log);
            }
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

// NOTE: We will get called from the main Nagios thread here, so we don't have
// to care about locking Nagios data structures etc. here.
int broker_external_command(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_external_command_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_EXTERNALCOMMAND_START:
            counterIncrement(Counter::commands);
            if (info->command_type == CMD_CUSTOM_COMMAND) {
                if (info->command_string == "_LOG"s) {
                    write_to_all_logs_(info->command_args);
                    counterIncrement(Counter::log_messages);
                    fl_core->triggers().notify_all(Triggers::Kind::log);
                } else if (info->command_string == "_ROTATE_LOGFILE"s) {
                    rotate_log_file(std::time(nullptr));
                }
            }
            fl_core->triggers().notify_all(Triggers::Kind::command);
            break;
        case NEBTYPE_EXTERNALCOMMAND_END:
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_state_change(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_statechange_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_STATECHANGE_START:
        case NEBTYPE_STATECHANGE_END:
            // Called after a host/service state change
            fl_core->triggers().notify_all(Triggers::Kind::state);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_adaptive_program(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_adaptive_program_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_ADAPTIVEPROGRAM_UPDATE:
            fl_core->triggers().notify_all(Triggers::Kind::program);
            break;
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_timed_event(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_timed_event_data *>(data);
    log_callback(callback_type, info->type);
    switch (info->type) {
        case NEBTYPE_TIMEDEVENT_ADD:
        case NEBTYPE_TIMEDEVENT_REMOVE:
        case NEBTYPE_TIMEDEVENT_EXECUTE:
        case NEBTYPE_TIMEDEVENT_DELAY:
        case NEBTYPE_TIMEDEVENT_SKIP:
        case NEBTYPE_TIMEDEVENT_SLEEP: {
            [[maybe_unused]] static auto once{(log_initial_states(), true)};
            g_timeperiods_cache->update(from_timeval(info->timestamp));
            break;
        }
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_process(int callback_type, void *data) {
    auto *info = static_cast<nebstruct_process_data *>(data);
    log_callback(callback_type, info->type);
    // The event types below are in chronological order.
    switch (info->type) {
        case NEBTYPE_PROCESS_PRELAUNCH:
            // Called prior to reading/parsing object configuration files.
            break;
        case NEBTYPE_PROCESS_START:
            // Called after reading all configuration objects and after passing
            // the pre-flight check. Called before entering daemon mode, opening
            // command pipe, starting worker threads, intitializing the status,
            // comments, downtime, performance and initial host/service
            // structures.
            try {
                auto now = std::chrono::system_clock::now();
                auto state_file_created = mk::state_file_created(
                    fl_paths.state_file_created_file, now);
                auto is_licensed =
                    mk::is_licensed(fl_paths.licensed_state_file);
                // NOLINTBEGIN(cppcoreguidelines-owning-memory)
                fl_core =
                    new NebCore(fl_downtimes, fl_comments, fl_paths, fl_limits,
                                fl_authorization, fl_data_encoding, fl_edition,
                                state_file_created);
                size_t num_services{0};
                fl_core->all_of_hosts([&num_services](const IHost &hst) {
                    num_services += hst.total_services();
                    return true;
                });
                mk::validate_license(state_file_created, is_licensed, now,
                                     num_services);
                fl_client_queue = new ClientQueue_t{};
                g_timeperiods_cache = new TimeperiodsCache(fl_logger_nagios);
                // NOLINTEND(cppcoreguidelines-owning-memory)
            } catch (const std::exception &e) {
                std::cerr << e.what() << "\n";
                exit(EXIT_FAILURE);  // NOLINT(concurrency-mt-unsafe)
            }
            break;
        case NEBTYPE_PROCESS_DAEMONIZE:
            // Called right after Nagios successfully "daemonizes"; that is,
            // detaches from the controlling terminal and is running in the
            // background.
            break;
        case NEBTYPE_PROCESS_EVENTLOOPSTART:
            // Called immediately prior to entering the main event execution.
            g_timeperiods_cache->update(from_timeval(info->timestamp));
            start_threads();
            fl_core->dumpPaths();
            break;
        case NEBTYPE_PROCESS_EVENTLOOPEND:
            // Called immediately after exiting the main event execution loop
            // (due to either a shutdown or a restart)
        case NEBTYPE_PROCESS_SHUTDOWN:
            // Invoked if exiting due to either a process-initiated (abnormal)
            // or a user-initiated (normal) shutdown
        case NEBTYPE_PROCESS_RESTART:
            // Invoked if exiting due to a user-initiated restart. Always
            // invoked after NEBTYPE_EVENLOOPEND.
        default:
            // We should never see other event types here.
            break;
    }
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

struct nagios_callback {
    int callback_type;
    int (*callback_func)(int, void *);
    std::string_view event_broker_option_name;
    int event_broker_option_flag;
};

const std::array<nagios_callback, 10> nagios_callbacks{{
    {
        .callback_type = NEBCALLBACK_COMMENT_DATA,
        .callback_func = broker_comment,
        .event_broker_option_name = "BROKER_COMMENT_DATA"sv,
        .event_broker_option_flag = BROKER_COMMENT_DATA,
    },
    {
        .callback_type = NEBCALLBACK_DOWNTIME_DATA,
        .callback_func = broker_downtime,
        .event_broker_option_name = "BROKER_DOWNTIME_DATA"sv,
        .event_broker_option_flag = BROKER_DOWNTIME_DATA,
    },
    {
        .callback_type = NEBCALLBACK_SERVICE_CHECK_DATA,
        .callback_func = broker_service_check,
        .event_broker_option_name = "BROKER_SERVICE_CHECKS"sv,
        .event_broker_option_flag = BROKER_SERVICE_CHECKS,
    },
    {
        .callback_type = NEBCALLBACK_HOST_CHECK_DATA,
        .callback_func = broker_host_check,
        .event_broker_option_name = "BROKER_HOST_CHECKS"sv,
        .event_broker_option_flag = BROKER_HOST_CHECKS,
    },
    {
        .callback_type = NEBCALLBACK_LOG_DATA,
        .callback_func = broker_log,
        .event_broker_option_name = "BROKER_LOGGED_DATA"sv,
        .event_broker_option_flag = BROKER_LOGGED_DATA,
    },
    {
        .callback_type = NEBCALLBACK_EXTERNAL_COMMAND_DATA,
        .callback_func = broker_external_command,
        .event_broker_option_name = "BROKER_EXTERNALCOMMAND_DATA"sv,
        .event_broker_option_flag = BROKER_EXTERNALCOMMAND_DATA,
    },
    {
        .callback_type = NEBCALLBACK_STATE_CHANGE_DATA,
        .callback_func = broker_state_change,
        .event_broker_option_name = "BROKER_STATECHANGE_DATA"sv,
        .event_broker_option_flag = BROKER_STATECHANGE_DATA,
    },
    {
        .callback_type = NEBCALLBACK_ADAPTIVE_PROGRAM_DATA,
        .callback_func = broker_adaptive_program,
        .event_broker_option_name = "BROKER_ADAPTIVE_DATA"sv,
        .event_broker_option_flag = BROKER_ADAPTIVE_DATA,
    },
    {
        .callback_type = NEBCALLBACK_PROCESS_DATA,
        .callback_func = broker_process,
        .event_broker_option_name = "BROKER_PROGRAM_STATE"sv,
        .event_broker_option_flag = BROKER_PROGRAM_STATE,
    },
    {
        .callback_type = NEBCALLBACK_TIMED_EVENT_DATA,
        .callback_func = broker_timed_event,
        .event_broker_option_name = "BROKER_TIMED_EVENTS"sv,
        .event_broker_option_flag = BROKER_TIMED_EVENTS,
    },
}};

void register_callbacks() {
    for (const auto &cb : nagios_callbacks) {
        if ((event_broker_options & cb.event_broker_option_flag) == 0) {
            throw generic_error{
                EINVAL, "need " + std::string{cb.event_broker_option_name} +
                            " (" + std::to_string(cb.event_broker_option_flag) +
                            ") event_broker_option enabled to work"};
        }
        neb_register_callback(cb.callback_type, fl_nagios_handle, 0,
                              cb.callback_func);
    }
}

void deregister_callbacks() {
    for (const auto &cb : nagios_callbacks) {
        neb_deregister_callback(cb.callback_type, cb.callback_func);
    }
}

std::filesystem::path check_path(const std::string &name,
                                 std::string_view path) {
    struct stat st{};
    if (stat(std::string{path}.c_str(), &st) != 0) {
        Error(fl_logger_nagios) << name << " '" << path << "' not existing!";
        return {};  // disable
    }
    if (access(std::string{path}.c_str(), R_OK) != 0) {
        Error(fl_logger_nagios) << name << " '" << path
                                << "' not readable, please fix permissions.";
        return {};  // disable
    }
    return path;
}

template <typename T>
T parse_number(std::string_view str) {
    T value{};
    auto [ptr, ec] = std::from_chars(str.begin(), str.end(), value);
    // TODO(sp) Error handling
    return ec != std::errc{} || ptr != str.end() ? T{} : value;
}

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
void livestatus_parse_argument(Logger *logger, std::string_view param_name,
                               std::string_view param_value) {
    Warning(logger) << "name=[" << param_name << "], value=[" << param_value
                    << "]\n";
    if (param_name == "debug"sv) {
        const int debug_level = parse_number<int>(param_value);
        if (debug_level >= 2) {
            fl_livestatus_log_level = LogLevel::debug;
        } else if (debug_level >= 1) {
            fl_livestatus_log_level = LogLevel::informational;
        } else {
            fl_livestatus_log_level = LogLevel::notice;
        }
        Notice(logger) << "setting log level to " << fl_livestatus_log_level;
    } else if (param_name == "max_cached_messages"sv) {
        fl_limits._max_cached_messages = parse_number<size_t>(param_value);
        Notice(logger) << "setting max number of cached log messages to "
                       << fl_limits._max_cached_messages;
    } else if (param_name == "max_lines_per_logfile"sv) {
        fl_limits._max_lines_per_logfile = parse_number<size_t>(param_value);
        Notice(logger) << "setting max number lines per logfile to "
                       << fl_limits._max_lines_per_logfile;
    } else if (param_name == "thread_stack_size"sv) {
        fl_thread_stack_size = parse_number<size_t>(param_value);
        Notice(logger) << "setting size of thread stacks to "
                       << fl_thread_stack_size;
    } else if (param_name == "max_response_size"sv) {
        fl_limits._max_response_size = parse_number<size_t>(param_value);
        Notice(logger) << "setting maximum response size to "
                       << fl_limits._max_response_size << " bytes ("
                       << (static_cast<double>(fl_limits._max_response_size) /
                           (1024.0 * 1024.0))
                       << " MB)";
    } else if (param_name == "num_client_threads"sv) {
        const int c = parse_number<int>(param_value);
        if (c <= 0 || c > 1000) {
            Warning(logger) << "cannot set num_client_threads to " << c
                            << ", must be > 0 and <= 1000";
        } else {
            Notice(logger) << "setting number of client threads to " << c;
            g_livestatus_threads = c;
        }
    } else if (param_name == "query_timeout"sv) {
        const int c = parse_number<int>(param_value);
        if (c < 0) {
            Warning(logger) << "query_timeout must be >= 0";
        } else {
            fl_query_timeout = std::chrono::milliseconds(c);
            if (c == 0) {
                Notice(logger) << "disabled query timeout!";
            } else {
                Notice(logger)
                    << "Setting timeout for reading a query to " << c << " ms";
            }
        }
    } else if (param_name == "idle_timeout"sv) {
        const int c = parse_number<int>(param_value);
        if (c < 0) {
            Warning(logger) << "idle_timeout must be >= 0";
        } else {
            fl_idle_timeout = std::chrono::milliseconds(c);
            if (c == 0) {
                Notice(logger) << "disabled idle timeout!";
            } else {
                Notice(logger) << "setting idle timeout to " << c << " ms";
            }
        }
    } else if (param_name == "service_authorization"sv) {
        if (param_value == "strict") {
            fl_authorization._service = ServiceAuthorization::strict;
        } else if (param_value == "loose") {
            fl_authorization._service = ServiceAuthorization::loose;
        } else {
            Warning(logger) << "invalid service authorization mode, "
                               "allowed are strict and loose";
        }
    } else if (param_name == "group_authorization"sv) {
        if (param_value == "strict") {
            fl_authorization._group = GroupAuthorization::strict;
        } else if (param_value == "loose") {
            fl_authorization._group = GroupAuthorization::loose;
        } else {
            Warning(logger)
                << "invalid group authorization mode, allowed are strict and loose";
        }
    } else if (param_name == "log_file"sv) {
        fl_paths.log_file = param_value;
    } else if (param_name == "crash_reports_path"sv) {
        fl_paths.crash_reports_directory =
            check_path("crash reports directory", param_value);
    } else if (param_name == "license_usage_history_path"sv) {
        fl_paths.license_usage_history_file =
            check_path("license usage history file", param_value);
    } else if (param_name == "mk_inventory_path"sv) {
        fl_paths.inventory_directory =
            check_path("inventory directory", param_value);
    } else if (param_name == "structured_status_path"sv) {
        fl_paths.structured_status_directory =
            check_path("structured status directory", param_value);
    } else if (param_name == "robotmk_html_log_path"sv) {
        fl_paths.robotmk_html_log_directory =
            check_path("robotmk html log directory", param_value);
    } else if (param_name == "mk_logwatch_path"sv) {
        fl_paths.logwatch_directory =
            check_path("logwatch directory", param_value);
    } else if (param_name == "prediction_path"sv) {
        fl_paths.prediction_directory =
            check_path("prediction directory", param_value);
    } else if (param_name == "mkeventd_socket"sv) {
        fl_paths.event_console_status_socket = param_value;
    } else if (param_name == "state_file_created_file"sv) {
        fl_paths.state_file_created_file = param_value;
    } else if (param_name == "licensed_state_file"sv) {
        fl_paths.licensed_state_file = param_value;
    } else if (param_name == "pnp_path"sv) {
        // The Nagios RRD metric file path begins with a symbolic link (/omd),
        // which must be resolved to its real path because RRDtool does not
        // handle symbolic links properly when processing flush commands in
        // rrdcached
        fl_paths.rrd_multiple_directory = std::filesystem::canonical(
            check_path("RRD multiple directory", param_value));
    } else if (param_name == "data_encoding"sv) {
        if (param_value == "utf8") {
            fl_data_encoding = Encoding::utf8;
        } else if (param_value == "latin1") {
            fl_data_encoding = Encoding::latin1;
        } else if (param_value == "mixed") {
            fl_data_encoding = Encoding::mixed;
        } else {
            Warning(logger) << "invalid data_encoding " << param_value
                            << ", allowed are utf8, latin1 and mixed";
        }
    } else if (param_name == "edition"sv) {
        fl_edition = param_value;
    } else if (param_name == "livecheck"sv) {
        Warning(logger) << "livecheck has been removed from Livestatus, sorry.";
    } else if (param_name == "disable_statehist_filtering"sv) {
        Warning(logger)
            << "the disable_statehist_filtering option has been removed, filtering is always active now.";
    } else {
        Warning(logger) << "ignoring invalid option " << param_name << "="
                        << param_value;
    }
}

void livestatus_parse_arguments(Logger *logger, const char *args_orig) {
    {
        // set default path to our logfile to be in the same path as nagios.log
        const std::string lf{log_file};
        auto slash = lf.rfind('/');
        fl_paths.log_file =
            (slash == std::string::npos ? "/tmp/" : lf.substr(0, slash + 1)) +
            "livestatus.log";
    }

    if (args_orig == nullptr) {
        return;  // no arguments, use default options
    }

    std::string_view args{args_orig};
    while (true) {
        args.remove_prefix(
            std::min(args.size(), args.find_first_not_of(mk::whitespace)));
        if (args.empty()) {
            break;
        }
        auto arg = args.substr(0, args.find_first_of(mk::whitespace));
        args.remove_prefix(std::min(args.size(), arg.size() + 1));
        auto equal_pos = arg.find('=');
        if (equal_pos == std::string_view::npos) {
            Warning(logger)
                << "### setting livestatus_socket=[" << arg << "]\n";
            fl_paths.livestatus_socket = arg;
        } else {
            auto param_name = arg.substr(0, equal_pos);
            arg.remove_prefix(std::min(arg.size(), param_name.size() + 1));
            livestatus_parse_argument(logger, param_name, arg);
        }
    }

    if (fl_paths.livestatus_socket.empty()) {  // Do we still need this?
        fl_paths.livestatus_socket = "/usr/local/nagios/var/rw/live";
    }
    const std::string sp{fl_paths.livestatus_socket};
    auto slash = sp.rfind('/');
    auto prefix = slash == std::string::npos ? "" : sp.substr(0, slash + 1);
    if (fl_paths.event_console_status_socket.empty()) {
        fl_paths.event_console_status_socket = prefix + "mkeventd/status";
    }
    // TODO(sp) Make this configurable.
    if (fl_paths.rrdcached_socket.empty()) {
        fl_paths.rrdcached_socket = prefix + "rrdcached.sock";
    }
    fl_paths.history_file = log_file == nullptr ? "" : log_file;
    fl_paths.history_archive_directory =
        log_archive_path == nullptr ? "" : log_archive_path;
}

void omd_advertize(Logger *logger) {
    Notice(logger) << "Livestatus by Checkmk GmbH started with PID "
                   << getpid();
#ifndef __TIMESTAMP__
#define __TIMESTAMP__ (__DATE__ " " __TIME__)
#endif

#ifdef __GNUC__
#define BUILD_CXX ("g++ " __VERSION__)
#elif defined(__VERSION)
#define BUILD_CXX __VERSION__
#else
#define BUILD_CXX "unknown C++ compiler"
#endif
    Notice(logger) << "version " << cmk::version() << " compiled "
                   << __TIMESTAMP__ << " with " << BUILD_CXX << ", using "
                   << RegExp::engine() << " regex engine";
    Notice(logger) << "please visit us at https://checkmk.com/";
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    if (const char *omd_site = getenv("OMD_SITE")) {
        Informational(logger)
            << "running on Checkmk site " << omd_site << ", cool.";
    } else {
        Notice(logger) << "Hint: Please try out Checkmk (https://checkmk.com/)";
    }
}
}  // namespace

// Called from Nagios after we have been loaded.
extern "C" int nebmodule_init(int flags __attribute__((__unused__)), char *args,
                              void *handle) {
    fl_logger_nagios = Logger::getLogger("nagios");
    fl_logger_nagios->setHandler(std::make_unique<NagiosHandler>());
    fl_logger_nagios->setUseParentHandlers(false);

    fl_nagios_handle = handle;
    livestatus_parse_arguments(fl_logger_nagios, args);
    omd_advertize(fl_logger_nagios);

    try {
        open_unix_socket();
        if (enable_environment_macros == 1) {
            Notice(fl_logger_nagios)
                << "environment_macros are enabled, this might decrease the "
                   "overall nagios performance";
        }
        register_callbacks();
        Informational(fl_logger_nagios)
            << "your event_broker_options are sufficient for livestatus.";
    } catch (const std::exception &e) {
        std::cerr << e.what() << "\n";
        ::exit(EXIT_FAILURE);  // NOLINT(concurrency-mt-unsafe)
    }

    /* Unfortunately, we cannot start our socket thread right now.
       Nagios demonizes *after* having loaded the NEB modules. When
       demonizing we are losing our thread. Therefore, we create the
       thread the first time one of our callbacks is called. Before
       that happens, we haven't got any data anyway... */

    Notice(fl_logger_nagios)
        << "finished initialization, further log messages go to "
        << fl_paths.log_file;
    return 0;
}

// Called from Nagios after before we are unloaded.
extern "C" int nebmodule_deinit(int flags __attribute__((__unused__)),
                                int reason __attribute__((__unused__))) {
    Notice(fl_logger_nagios) << "deinitializing";
    terminate_threads();
    close_unix_socket();
    deregister_callbacks();

    // NOLINTBEGIN(cppcoreguidelines-owning-memory)
    delete g_timeperiods_cache;
    g_timeperiods_cache = nullptr;

    delete fl_client_queue;
    fl_client_queue = nullptr;

    delete fl_core;
    fl_core = nullptr;
    // NOLINTEND(cppcoreguidelines-owning-memory)

    return 0;
}
