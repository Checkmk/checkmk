// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// Needed for S_ISSOCK
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define _XOPEN_SOURCE 500

// https://github.com/include-what-you-use/include-what-you-use/issues/166
// IWYU pragma: no_include <ext/alloc_traits.h>
#include "config.h"
#include <fcntl.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include "ChronoUtils.h"
#include "ClientQueue.h"
#include "InputBuffer.h"
#include "Logger.h"
#include "NagiosCore.h"
#include "OutputBuffer.h"
#include "Poller.h"
#include "RegExp.h"
#include "TimeperiodsCache.h"
#include "Triggers.h"
#include "auth.h"
#include "data_encoding.h"
#include "global_counters.h"
#include "nagios.h"
#include "strutil.h"

NEB_API_VERSION(CURRENT_NEB_API_VERSION)
#ifndef NAGIOS4
extern int event_broker_options;
#else
extern unsigned long event_broker_options;
#endif  // NAGIOS4
extern int enable_environment_macros;

// maximum idle time for connection in keep alive state
static std::chrono::milliseconds fl_idle_timeout = std::chrono::minutes(5);

// maximum time for reading a query
static std::chrono::milliseconds fl_query_timeout = std::chrono::seconds(10);

// allow 10 concurrent connections per default
size_t g_livestatus_threads = 10;
// current number of queued connections (for statistics)
int g_num_queued_connections = 0;
// current number of active connections (for statistics)
std::atomic_int32_t g_livestatus_active_connections{0};
size_t g_thread_stack_size = 1024 * 1024; /* stack size of threads */

void *g_nagios_handle;
int g_unix_socket = -1;
int g_max_fd_ever = 0;

static NagiosPaths fl_paths;

static bool fl_should_terminate = false;

struct ThreadInfo {
    pthread_t id;
    std::string name;
};

static std::vector<ThreadInfo> fl_thread_info;
static thread_local ThreadInfo *tl_info;

static NagiosLimits fl_limits;

int g_thread_running = 0;

static NagiosAuthorization fl_authorization;

Encoding fl_data_encoding{Encoding::utf8};

static Logger *fl_logger_nagios = nullptr;
static LogLevel fl_livestatus_log_level = LogLevel::notice;
static ClientQueue *fl_client_queue = nullptr;
TimeperiodsCache *g_timeperiods_cache = nullptr;

/* simple statistics data for TableStatus */
extern service *service_list;
extern int log_initial_states;

int g_num_hosts;
int g_num_services;

static NagiosCore *fl_core = nullptr;

void count_hosts() {
    extern host *host_list;
    g_num_hosts = 0;
    for (host *h = host_list; h != nullptr; h = h->next) {
        g_num_hosts++;
    }
}

void count_services() {
    g_num_services = 0;
    for (service *s = service_list; s != nullptr; s = s->next) {
        g_num_services++;
    }
}

void *voidp;

void livestatus_count_fork() { counterIncrement(Counter::forks); }

void livestatus_cleanup_after_fork() {
    // 4.2.2010: Deactivate the cleanup function. It might cause
    // more trouble than it tries to avoid. It might lead to a deadlock
    // with Nagios' fork()-mechanism...
    // store_deinit();
    struct stat st;

    int i;
    // We need to close our server and client sockets. Otherwise
    // our connections are inherited to host and service checks.
    // If we close our client connection in such a situation,
    // the connection will still be open since and the client will
    // hang while trying to read further data. And the CLOEXEC is
    // not atomic :-(

    // Eventuell sollte man hier anstelle von store_deinit() nicht
    // darauf verlassen, dass die ClientQueue alle Verbindungen zumacht.
    // Es sind ja auch Dateideskriptoren offen, die von Threads gehalten
    // werden und nicht mehr in der Queue sind. Und in store_deinit()
    // wird mit mutexes rumgemacht....
    for (i = 3; i < g_max_fd_ever; i++) {
        if (0 == fstat(i, &st) && S_ISSOCK(st.st_mode)) {
            close(i);
        }
    }
}

void *main_thread(void *data) {
    tl_info = static_cast<ThreadInfo *>(data);
    auto logger = fl_core->loggerLivestatus();
    while (!fl_should_terminate) {
        do_statistics();

        Poller poller;
        poller.addFileDescriptor(g_unix_socket, PollEvents::in);
        int retval = poller.poll(std::chrono::milliseconds(2500));
        if (retval > 0 &&
            poller.isFileDescriptorSet(g_unix_socket, PollEvents::in)) {
#if HAVE_ACCEPT4
            int cc = accept4(g_unix_socket, nullptr, nullptr, SOCK_CLOEXEC);
#else
            int cc = accept(g_unix_socket, nullptr, nullptr);
#endif
            if (cc == -1) {
                generic_error ge("cannot accept client connection");
                Warning(logger) << ge;
                continue;
            }
#if !HAVE_ACCEPT4
            if (fcntl(cc, F_SETFD, FD_CLOEXEC) == -1) {
                generic_error ge(
                    "cannot set close-on-exec bit on client socket");
                Alert(logger) << ge;
                break;
            }
#endif
            if (cc > g_max_fd_ever) {
                g_max_fd_ever = cc;
            }
            fl_client_queue->addConnection(cc);  // closes fd
            g_num_queued_connections++;
            counterIncrement(Counter::connections);
        }
    }
    Notice(logger) << "socket thread has terminated";
    return voidp;
}

void *client_thread(void *data) {
    tl_info = static_cast<ThreadInfo *>(data);
    auto logger = fl_core->loggerLivestatus();
    while (!fl_should_terminate) {
        int cc = fl_client_queue->popConnection();
        g_num_queued_connections--;
        g_livestatus_active_connections++;
        if (cc >= 0) {
            Debug(logger) << "accepted client connection on fd " << cc;
            InputBuffer input_buffer(cc, fl_should_terminate, logger,
                                     fl_query_timeout, fl_idle_timeout);
            bool keepalive = true;
            unsigned requestnr = 0;
            while (keepalive && !fl_should_terminate) {
                if (++requestnr > 1) {
                    Debug(logger) << "handling request " << requestnr
                                  << " on same connection";
                }
                counterIncrement(Counter::requests);
                OutputBuffer output_buffer(cc, fl_should_terminate, logger);
                keepalive = fl_core->answerRequest(input_buffer, output_buffer);
            }
            close(cc);
        }
        g_livestatus_active_connections--;
    }
    return voidp;
}

namespace {
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
        // TODO(sp) The Nagios headers are (once again) not const-correct...
        write_to_all_logs(const_cast<char *>(os.str().c_str()),
                          NSLOG_INFO_MESSAGE);
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
}  // namespace

void start_threads() {
    count_hosts();
    count_services();

    if (g_thread_running == 0) {
        auto logger = fl_core->loggerLivestatus();
        logger->setLevel(fl_livestatus_log_level);
        logger->setUseParentHandlers(false);
        try {
            logger->setHandler(
                std::make_unique<LivestatusHandler>(fl_paths._logfile));
        } catch (const generic_error &ex) {
            Warning(fl_logger_nagios) << ex;
        }

        Informational(fl_logger_nagios)
            << "starting main thread and " << g_livestatus_threads
            << " client threads";

        pthread_atfork(livestatus_count_fork, nullptr,
                       livestatus_cleanup_after_fork);

        pthread_attr_t attr;
        pthread_attr_init(&attr);
        size_t defsize;
        if (pthread_attr_getstacksize(&attr, &defsize) == 0) {
            Debug(fl_logger_nagios) << "default stack size is " << defsize;
        }
        if (pthread_attr_setstacksize(&attr, g_thread_stack_size) != 0) {
            Warning(fl_logger_nagios)
                << "cannot set thread stack size to " << g_thread_stack_size;
        } else {
            Debug(fl_logger_nagios)
                << "setting thread stack size to " << g_thread_stack_size;
        }

        fl_thread_info.resize(g_livestatus_threads + 1);
        for (auto &info : fl_thread_info) {
            ptrdiff_t idx = &info - &fl_thread_info[0];
            if (idx == 0) {
                // start thread that listens on socket
                info.name = "main";
                pthread_create(&info.id, nullptr, main_thread, &info);
                // Our current thread (i.e. the main one, confusing terminology)
                // needs thread-local infos for logging, too.
                tl_info = &info;
            } else {
                info.name = "client " + std::to_string(idx);
                pthread_create(&info.id, &attr, client_thread, &info);
            }
        }

        g_thread_running = 1;
        pthread_attr_destroy(&attr);
    }
}

void terminate_threads() {
    if (g_thread_running != 0) {
        fl_should_terminate = true;
        Informational(fl_logger_nagios) << "waiting for main to terminate...";
        pthread_join(fl_thread_info[0].id, nullptr);
        Informational(fl_logger_nagios)
            << "waiting for client threads to terminate...";
        fl_client_queue->terminate();
        for (const auto &info : fl_thread_info) {
            if (pthread_join(info.id, nullptr) != 0) {
                Warning(fl_logger_nagios)
                    << "could not join thread " << info.name;
            }
        }
        Informational(fl_logger_nagios)
            << "main thread + " << g_livestatus_threads
            << " client threads have finished";
        g_thread_running = 0;
        fl_should_terminate = false;
    }
}

bool open_unix_socket() {
    struct stat st;
    if (stat(fl_paths._socket.c_str(), &st) == 0) {
        if (unlink(fl_paths._socket.c_str()) == 0) {
            Debug(fl_logger_nagios)
                << "removed old socket file " << fl_paths._socket;
        } else {
            generic_error ge("cannot remove old socket file " +
                             fl_paths._socket);
            Alert(fl_logger_nagios) << ge;
            return false;
        }
    }

    g_unix_socket = socket(PF_UNIX, SOCK_STREAM, 0);
    g_max_fd_ever = g_unix_socket;
    if (g_unix_socket < 0) {
        generic_error ge("cannot create UNIX socket");
        Critical(fl_logger_nagios) << ge;
        return false;
    }

    // Imortant: close on exec -> check plugins must not inherit it!
    if (fcntl(g_unix_socket, F_SETFD, FD_CLOEXEC) == -1) {
        generic_error ge("cannot set close-on-exec bit on socket");
        Alert(fl_logger_nagios) << ge;
        close(g_unix_socket);
        return false;
    }

    // Bind it to its address. This creates the file with the name
    // fl_paths._socket
    struct sockaddr_un sockaddr;
    sockaddr.sun_family = AF_UNIX;
    strncpy(sockaddr.sun_path, fl_paths._socket.c_str(),
            sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    if (bind(g_unix_socket, reinterpret_cast<struct sockaddr *>(&sockaddr),
             sizeof(sockaddr)) < 0) {
        generic_error ge("cannot bind UNIX socket to address " +
                         fl_paths._socket);
        Error(fl_logger_nagios) << ge;
        close(g_unix_socket);
        return false;
    }

    // Make writable group members (fchmod didn't do nothing for me. Don't know
    // why!)
    if (0 != chmod(fl_paths._socket.c_str(), 0660)) {
        generic_error ge("cannot change file permissions for UNIX socket at " +
                         fl_paths._socket + " to 0660");
        Error(fl_logger_nagios) << ge;
        close(g_unix_socket);
        return false;
    }

    if (0 != listen(g_unix_socket, 3 /* backlog */)) {
        generic_error ge("cannot listen to UNIX socket at " + fl_paths._socket);
        Error(fl_logger_nagios) << ge;
        close(g_unix_socket);
        return false;
    }

    Informational(fl_logger_nagios)
        << "opened UNIX socket at " << fl_paths._socket;
    return true;
}

void close_unix_socket() {
    unlink(fl_paths._socket.c_str());
    if (g_unix_socket >= 0) {
        close(g_unix_socket);
        g_unix_socket = -1;
    }
}

int broker_host(int event_type __attribute__((__unused__)),
                void *data __attribute__((__unused__))) {
    counterIncrement(Counter::neb_callbacks);
    return 0;
}

int broker_check(int event_type, void *data) {
    int result = NEB_OK;
    if (event_type == NEBCALLBACK_SERVICE_CHECK_DATA) {
        auto c = static_cast<nebstruct_service_check_data *>(data);
        if (c->type == NEBTYPE_SERVICECHECK_PROCESSED) {
            counterIncrement(Counter::service_checks);
        }
    } else if (event_type == NEBCALLBACK_HOST_CHECK_DATA) {
        auto c = static_cast<nebstruct_host_check_data *>(data);
        if (c->type == NEBTYPE_HOSTCHECK_PROCESSED) {
            counterIncrement(Counter::host_checks);
        }
    }
    fl_core->triggers().notify_all(Triggers::Kind::check);
    return result;
}

int broker_comment(int event_type __attribute__((__unused__)), void *data) {
    auto co = static_cast<nebstruct_comment_data *>(data);
    fl_core->registerComment(co);
    counterIncrement(Counter::neb_callbacks);
    fl_core->triggers().notify_all(Triggers::Kind::comment);
    return 0;
}

int broker_downtime(int event_type __attribute__((__unused__)), void *data) {
    auto dt = static_cast<nebstruct_downtime_data *>(data);
    fl_core->registerDowntime(dt);
    counterIncrement(Counter::neb_callbacks);
    fl_core->triggers().notify_all(Triggers::Kind::downtime);
    return 0;
}

int broker_log(int event_type __attribute__((__unused__)),
               void *data __attribute__((__unused__))) {
    counterIncrement(Counter::neb_callbacks);
    counterIncrement(Counter::log_messages);
    // NOTE: We use logging very early, even before the core is instantiated!
    if (fl_core != nullptr) {
        fl_core->triggers().notify_all(Triggers::Kind::log);
    }
    return 0;
}

// called twice (start/end) for each external command, even builtin ones
int broker_command(int event_type __attribute__((__unused__)), void *data) {
    auto sc = static_cast<nebstruct_external_command_data *>(data);
    if (sc->type == NEBTYPE_EXTERNALCOMMAND_START) {
        counterIncrement(Counter::commands);
        if (sc->command_type == CMD_CUSTOM_COMMAND &&
            strcmp(sc->command_string, "_LOG") == 0) {
            write_to_all_logs(sc->command_args, -1);
            counterIncrement(Counter::log_messages);
            fl_core->triggers().notify_all(Triggers::Kind::log);
        }
    }
    counterIncrement(Counter::neb_callbacks);
    fl_core->triggers().notify_all(Triggers::Kind::command);
    return 0;
}

int broker_state(int event_type __attribute__((__unused__)),
                 void *data __attribute__((__unused__))) {
    counterIncrement(Counter::neb_callbacks);
    fl_core->triggers().notify_all(Triggers::Kind::state);
    return 0;
}

int broker_program(int event_type __attribute__((__unused__)),
                   void *data __attribute__((__unused__))) {
    counterIncrement(Counter::neb_callbacks);
    fl_core->triggers().notify_all(Triggers::Kind::program);
    return 0;
}

void livestatus_log_initial_states() {
    extern scheduled_downtime *scheduled_downtime_list;
    // It's a bit unclear if we need to log downtimes of hosts *before* their
    // corresponding service downtimes, so let's play safe...
    for (auto dt = scheduled_downtime_list; dt != nullptr; dt = dt->next) {
        if (dt->is_in_effect != 0 && dt->type == HOST_DOWNTIME) {
            Informational(fl_logger_nagios)
                << "HOST DOWNTIME ALERT: " << dt->host_name << ";STARTED;"
                << dt->comment;
        }
    }
    for (auto dt = scheduled_downtime_list; dt != nullptr; dt = dt->next) {
        if (dt->is_in_effect != 0 && dt->type == SERVICE_DOWNTIME) {
            Informational(fl_logger_nagios)
                << "SERVICE DOWNTIME ALERT: " << dt->host_name << ";"
                << dt->service_description << ";STARTED;" << dt->comment;
        }
    }
    g_timeperiods_cache->logCurrentTimeperiods();
}

int broker_event(int event_type __attribute__((__unused__)), void *data) {
    counterIncrement(Counter::neb_callbacks);
    auto ts = static_cast<struct nebstruct_timed_event_struct *>(data);
    if (ts->event_type == EVENT_LOG_ROTATION) {
        if (g_thread_running == 1) {
            livestatus_log_initial_states();
        } else if (log_initial_states == 1) {
            // initial info during startup
            Informational(fl_logger_nagios) << "logging initial states";
        }
    }
    g_timeperiods_cache->update(from_timeval(ts->timestamp));
    return 0;
}

int broker_process(int event_type __attribute__((__unused__)), void *data) {
    auto ps = static_cast<struct nebstruct_process_struct *>(data);
    switch (ps->type) {
        case NEBTYPE_PROCESS_START:
            fl_core = new NagiosCore(fl_paths, fl_limits, fl_authorization,
                                     fl_data_encoding);
            fl_client_queue = new ClientQueue();
            g_timeperiods_cache = new TimeperiodsCache(fl_logger_nagios);
            break;
        case NEBTYPE_PROCESS_EVENTLOOPSTART:
            g_timeperiods_cache->update(from_timeval(ps->timestamp));
            start_threads();
            break;
        default:
            break;
    }
    return 0;
}

int verify_event_broker_options() {
    int errors = 0;
    if ((event_broker_options & BROKER_PROGRAM_STATE) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_PROGRAM_STATE (" << BROKER_PROGRAM_STATE
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_TIMED_EVENTS) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_TIMED_EVENTS (" << BROKER_TIMED_EVENTS
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_SERVICE_CHECKS) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_SERVICE_CHECKS (" << BROKER_SERVICE_CHECKS
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_HOST_CHECKS) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_HOST_CHECKS (" << BROKER_HOST_CHECKS
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_LOGGED_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_LOGGED_DATA (" << BROKER_LOGGED_DATA
            << ") event_broker_option enabled to work.",
            errors++;
    }
    if ((event_broker_options & BROKER_COMMENT_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_COMMENT_DATA (" << BROKER_COMMENT_DATA
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_DOWNTIME_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_DOWNTIME_DATA (" << BROKER_DOWNTIME_DATA
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_STATUS_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_STATUS_DATA (" << BROKER_STATUS_DATA
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_ADAPTIVE_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_ADAPTIVE_DATA (" << BROKER_ADAPTIVE_DATA
            << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_EXTERNALCOMMAND_DATA) == 0) {
        Critical(fl_logger_nagios) << "need BROKER_EXTERNALCOMMAND_DATA ("
                                   << BROKER_EXTERNALCOMMAND_DATA
                                   << ") event_broker_option enabled to work.";
        errors++;
    }
    if ((event_broker_options & BROKER_STATECHANGE_DATA) == 0) {
        Critical(fl_logger_nagios)
            << "need BROKER_STATECHANGE_DATA (" << BROKER_STATECHANGE_DATA
            << ") event_broker_option enabled to work.";
        errors++;
    }

    return static_cast<int>(errors == 0);
}

void register_callbacks() {
    neb_register_callback(NEBCALLBACK_HOST_STATUS_DATA, g_nagios_handle, 0,
                          broker_host);  // Needed to start threads
    neb_register_callback(NEBCALLBACK_COMMENT_DATA, g_nagios_handle, 0,
                          broker_comment);  // dynamic data
    neb_register_callback(NEBCALLBACK_DOWNTIME_DATA, g_nagios_handle, 0,
                          broker_downtime);  // dynamic data
    neb_register_callback(NEBCALLBACK_SERVICE_CHECK_DATA, g_nagios_handle, 0,
                          broker_check);  // only for statistics
    neb_register_callback(NEBCALLBACK_HOST_CHECK_DATA, g_nagios_handle, 0,
                          broker_check);  // only for statistics
    neb_register_callback(NEBCALLBACK_LOG_DATA, g_nagios_handle, 0,
                          broker_log);  // only for trigger 'log'
    neb_register_callback(NEBCALLBACK_EXTERNAL_COMMAND_DATA, g_nagios_handle, 0,
                          broker_command);  // only for trigger 'command'
    neb_register_callback(NEBCALLBACK_STATE_CHANGE_DATA, g_nagios_handle, 0,
                          broker_state);  // only for trigger 'state'
    neb_register_callback(NEBCALLBACK_ADAPTIVE_PROGRAM_DATA, g_nagios_handle, 0,
                          broker_program);  // only for trigger 'program'
    neb_register_callback(NEBCALLBACK_PROCESS_DATA, g_nagios_handle, 0,
                          broker_process);  // used for starting threads
    neb_register_callback(NEBCALLBACK_TIMED_EVENT_DATA, g_nagios_handle, 0,
                          broker_event);  // used for timeperiods cache
}

void deregister_callbacks() {
    neb_deregister_callback(NEBCALLBACK_HOST_STATUS_DATA, broker_host);
    neb_deregister_callback(NEBCALLBACK_COMMENT_DATA, broker_comment);
    neb_deregister_callback(NEBCALLBACK_DOWNTIME_DATA, broker_downtime);
    neb_deregister_callback(NEBCALLBACK_SERVICE_CHECK_DATA, broker_check);
    neb_deregister_callback(NEBCALLBACK_HOST_CHECK_DATA, broker_check);
    neb_deregister_callback(NEBCALLBACK_LOG_DATA, broker_log);
    neb_deregister_callback(NEBCALLBACK_EXTERNAL_COMMAND_DATA, broker_command);
    neb_deregister_callback(NEBCALLBACK_STATE_CHANGE_DATA, broker_state);
    neb_deregister_callback(NEBCALLBACK_ADAPTIVE_PROGRAM_DATA, broker_program);
    neb_deregister_callback(NEBCALLBACK_PROCESS_DATA, broker_program);
    neb_deregister_callback(NEBCALLBACK_TIMED_EVENT_DATA, broker_event);
}

std::string check_path(const std::string &name, const std::string &path) {
    struct stat st;
    if (stat(path.c_str(), &st) != 0) {
        Error(fl_logger_nagios) << name << " '" << path << "' not existing!";
        return {};  // disable
    }
    if (access(path.c_str(), R_OK) != 0) {
        Error(fl_logger_nagios) << name << " '" << path
                                << "' not readable, please fix permissions.";
        return {};  // disable
    }
    return path;
}

void livestatus_parse_arguments(Logger *logger, const char *args_orig) {
    {
        // set default path to our logfile to be in the same path as nagios.log
        extern char *log_file;
        std::string lf{log_file};
        auto slash = lf.rfind('/');
        fl_paths._logfile =
            (slash == std::string::npos ? "/tmp/" : lf.substr(0, slash + 1)) +
            "livestatus.log";
    }

    if (args_orig == nullptr) {
        return;  // no arguments, use default options
    }

    // TODO(sp) Nuke next_field and friends. Use C++ strings everywhere.
    std::vector<char> args_buf(args_orig, args_orig + strlen(args_orig) + 1);
    char *args = &args_buf[0];
    while (char *token = next_field(&args)) {
        /* find = */
        char *part = token;
        std::string left = safe_next_token(&part, '=');
        const char *right_token = next_token(&part, 0);
        if (right_token == nullptr) {
            fl_paths._socket = left;
        } else {
            std::string right{right_token};
            if (left == "debug") {
                int debug_level = atoi(right.c_str());
                if (debug_level >= 2) {
                    fl_livestatus_log_level = LogLevel::debug;
                } else if (debug_level >= 1) {
                    fl_livestatus_log_level = LogLevel::informational;
                } else {
                    fl_livestatus_log_level = LogLevel::notice;
                }
                Notice(logger)
                    << "setting debug level to " << fl_livestatus_log_level;
            } else if (left == "log_file") {
                fl_paths._logfile = right;
            } else if (left == "mkeventd_socket") {
                fl_paths._mkeventd_socket = right;
            } else if (left == "max_cached_messages") {
                fl_limits._max_cached_messages =
                    strtoul(right.c_str(), nullptr, 10);
                Notice(logger)
                    << "setting max number of cached log messages to "
                    << fl_limits._max_cached_messages;
            } else if (left == "max_lines_per_logfile") {
                fl_limits._max_lines_per_logfile =
                    strtoul(right.c_str(), nullptr, 10);
                Notice(logger) << "setting max number lines per logfile to "
                               << fl_limits._max_lines_per_logfile;
            } else if (left == "thread_stack_size") {
                g_thread_stack_size = strtoul(right.c_str(), nullptr, 10);
                Notice(logger) << "setting size of thread stacks to "
                               << g_thread_stack_size;
            } else if (left == "max_response_size") {
                fl_limits._max_response_size =
                    strtoul(right.c_str(), nullptr, 10);
                Notice(logger)
                    << "setting maximum response size to "
                    << fl_limits._max_response_size << " bytes ("
                    << (fl_limits._max_response_size / (1024.0 * 1024.0))
                    << " MB)";
            } else if (left == "num_client_threads") {
                int c = atoi(right.c_str());
                if (c <= 0 || c > 1000) {
                    Warning(logger) << "cannot set num_client_threads to " << c
                                    << ", must be > 0 and <= 1000";
                } else {
                    Notice(logger)
                        << "setting number of client threads to " << c;
                    g_livestatus_threads = c;
                }
            } else if (left == "query_timeout") {
                int c = atoi(right.c_str());
                if (c < 0) {
                    Warning(logger) << "query_timeout must be >= 0";
                } else {
                    fl_query_timeout = std::chrono::milliseconds(c);
                    if (c == 0) {
                        Notice(logger) << "disabled query timeout!";
                    } else {
                        Notice(logger)
                            << "Setting timeout for reading a query to " << c
                            << " ms";
                    }
                }
            } else if (left == "idle_timeout") {
                int c = atoi(right.c_str());
                if (c < 0) {
                    Warning(logger) << "idle_timeout must be >= 0";
                } else {
                    fl_idle_timeout = std::chrono::milliseconds(c);
                    if (c == 0) {
                        Notice(logger) << "disabled idle timeout!";
                    } else {
                        Notice(logger)
                            << "setting idle timeout to " << c << " ms";
                    }
                }
            } else if (left == "service_authorization") {
                if (right == "strict") {
                    fl_authorization._service = AuthorizationKind::strict;
                } else if (right == "loose") {
                    fl_authorization._service = AuthorizationKind::loose;
                } else {
                    Warning(logger) << "invalid service authorization mode, "
                                       "allowed are strict and loose";
                }
            } else if (left == "group_authorization") {
                if (right == "strict") {
                    fl_authorization._group = AuthorizationKind::strict;
                } else if (right == "loose") {
                    fl_authorization._group = AuthorizationKind::loose;
                } else {
                    Warning(logger)
                        << "invalid group authorization mode, allowed are strict and loose";
                }
            } else if (left == "pnp_path") {
                fl_paths._pnp = check_path("PNP perfdata directory", right);
            } else if (left == "mk_inventory_path") {
                fl_paths._mk_inventory =
                    check_path("Check_MK Inventory directory", right);
            } else if (left == "structured_status_path") {
                fl_paths._structured_status =
                    check_path("Check_MK structured status directory", right);
            } else if (left == "mk_logwatch_path") {
                fl_paths._mk_logwatch =
                    check_path("Check_MK logwatch directory", right);
            } else if (left == "data_encoding") {
                if (right == "utf8") {
                    fl_data_encoding = Encoding::utf8;
                } else if (right == "latin1") {
                    fl_data_encoding = Encoding::latin1;
                } else if (right == "mixed") {
                    fl_data_encoding = Encoding::mixed;
                } else {
                    Warning(logger) << "invalid data_encoding " << right
                                    << ", allowed are utf8, latin1 and mixed";
                }
            } else if (left == "livecheck") {
                Warning(logger)
                    << "livecheck has been removed from Livestatus, sorry.";
            } else if (left == "disable_statehist_filtering") {
                Warning(logger)
                    << "the disable_statehist_filtering option has been removed, filtering is always active now.";
            } else {
                Warning(logger)
                    << "ignoring invalid option " << left << "=" << right;
            }
        }
    }

    if (fl_paths._mkeventd_socket.empty()) {
        std::string sp{fl_paths._socket};
        auto slash = sp.rfind('/');
        fl_paths._mkeventd_socket =
            (slash == std::string::npos ? "" : sp.substr(0, slash + 1)) +
            "mkeventd/status";
    }
}

void omd_advertize(Logger *logger) {
    Notice(logger) << "Livestatus by Mathias Kettner started with PID "
                   << getpid();
    Notice(logger) << "version " << VERSION << " compiled " << BUILD_DATE
                   << " on " << BUILD_HOSTNAME;
    Notice(logger) << "built with " << BUILD_CXX << ", using "
                   << RegExp::engine() << " regex engine";
    Notice(logger) << "please visit us at http://mathias-kettner.de/";
    fl_paths.dump(logger);
    if (char *omd_site = getenv("OMD_SITE")) {
        Informational(logger)
            << "running on OMD site " << omd_site << ", cool.";
    } else {
        Notice(logger)
            << "Hint: Please try out OMD - the Open Monitoring Distribution";
        Notice(logger) << "Please visit OMD at http://omdistro.org";
    }
}

// Called from Nagios after we have been loaded.
extern "C" int nebmodule_init(int flags __attribute__((__unused__)), char *args,
                              void *handle) {
    fl_logger_nagios = Logger::getLogger("nagios");
    fl_logger_nagios->setHandler(std::make_unique<NagiosHandler>());
    fl_logger_nagios->setUseParentHandlers(false);

    g_nagios_handle = handle;
    livestatus_parse_arguments(fl_logger_nagios, args);
    omd_advertize(fl_logger_nagios);

    if (!open_unix_socket()) {
        return 1;
    }

    if (verify_event_broker_options() == 0) {
        Critical(fl_logger_nagios)
            << "bailing out, please fix event_broker_options.";
        Critical(fl_logger_nagios)
            << "hint: your event_broker_options are set to "
            << event_broker_options << ", try setting it to -1.";
        return 1;
    }
    Informational(fl_logger_nagios)
        << "your event_broker_options are sufficient for livestatus.";

    if (enable_environment_macros == 1) {
        Notice(fl_logger_nagios)
            << "environment_macros are enabled, this might decrease the "
               "overall nagios performance";
    }

    register_callbacks();

    /* Unfortunately, we cannot start our socket thread right now.
       Nagios demonizes *after* having loaded the NEB modules. When
       demonizing we are losing our thread. Therefore, we create the
       thread the first time one of our callbacks is called. Before
       that happens, we haven't got any data anyway... */

    Notice(fl_logger_nagios)
        << "finished initialization, further log messages go to "
        << fl_paths._logfile;
    return 0;
}

// Called from Nagios after before we are unloaded.
extern "C" int nebmodule_deinit(int flags __attribute__((__unused__)),
                                int reason __attribute__((__unused__))) {
    Notice(fl_logger_nagios) << "deinitializing";
    terminate_threads();
    close_unix_socket();
    deregister_callbacks();

    delete g_timeperiods_cache;
    g_timeperiods_cache = nullptr;

    delete fl_client_queue;
    fl_client_queue = nullptr;

    delete fl_core;
    fl_core = nullptr;

    return 0;
}
