// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// An LD_PRELOAD fake of getaddrinfo(), connect() and poll(). It resolves
// "*.test" to FAKE_NETWORK_ADDRESSES, "ADDRESS[#PORT],...", of the family asked
// for, other names as usual. Further variables:
// - FAKE_NETWORK_DELAY: the seconds each lookup takes
// - FAKE_NETWORK_IPV6_DELAY: extra seconds for IPv6 lookups
// - FAKE_NETWORK_SLOW_CONNECT=N: poll() hides the socket of the N-th
//   connect() until the next connect()
// - FAKE_NETWORK_LOG: a file of native int pairs, (0, timeout in ms) per
//   poll() and (1, 0) per connect()

#include <dlfcn.h>
#include <fcntl.h>
#include <netdb.h>
#include <poll.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

typedef int (*getaddrinfo_function)(const char *, const char *,
                                    const struct addrinfo *,
                                    struct addrinfo **);

typedef int (*connect_function)(int, const struct sockaddr *, socklen_t);

typedef int (*poll_function)(struct pollfd *, nfds_t, int);

// This is getaddrinfo() for the linker. With a name of its own for the
// compiler, clang-tidy doesn't insist on the parameter names of <netdb.h>.
int fake_getaddrinfo(const char *node, const char *service,
                     const struct addrinfo *hints, struct addrinfo **res)
    __asm__("getaddrinfo");

// Likewise, this is connect() for the linker.
int fake_connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen)
    __asm__("connect");

// Likewise, this is poll() for the linker.
int fake_poll(struct pollfd *fds, nfds_t nfds, int timeout) __asm__("poll");

// The connect() calls started so far, and the socket of the slow one
// NOLINTBEGIN(cppcoreguidelines-avoid-non-const-global-variables)
static atomic_int connects_started;
static atomic_int slow_socket;
// NOLINTEND(cppcoreguidelines-avoid-non-const-global-variables)

// The seconds in the environment variable, maybe with a fraction, 0 if unset.
static double seconds_in(const char *variable) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const char *seconds = getenv(variable);
    return seconds == NULL ? 0 : strtod(seconds, NULL);
}

// The number in the environment variable, 0 if unset.
static long number_in(const char *variable) {
    const int decimal = 10;
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const char *number = getenv(variable);
    return number == NULL ? 0 : strtol(number, NULL, decimal);
}

static void sleep_for(double seconds) {
    const double nanoseconds_per_second = 1e9;
    const time_t whole = (time_t)seconds;
    const struct timespec duration = {
        .tv_sec = whole,
        .tv_nsec = (long)((seconds - (double)whole) * nanoseconds_per_second)};
    nanosleep(&duration, NULL);
}

// Whether the numeric address has the family asked for, if any.
static int has_family(const char *address, int family) {
    return family == AF_UNSPEC ||
           family == (strchr(address, ':') == NULL ? AF_INET : AF_INET6);
}

// Resolves "ADDRESS[#PORT]" to its addresses of the family asked for, if any.
static int resolve_entry(getaddrinfo_function real_getaddrinfo, char *entry,
                         const char *service, const struct addrinfo *hints,
                         struct addrinfo **found) {
    char *port = strchr(entry, '#');
    if (port != NULL) {
        *port++ = '\0';
    }
    *found = NULL;
    if (!has_family(entry, hints == NULL ? AF_UNSPEC : hints->ai_family)) {
        return 0;
    }
    return real_getaddrinfo(entry, port == NULL ? service : port, hints, found);
}

// Whether the name ends with the suffix.
static int has_suffix(const char *node, const char *suffix) {
    const size_t length = node == NULL ? 0 : strlen(node);
    return length >= strlen(suffix) &&
           strcmp(node + length - strlen(suffix), suffix) == 0;
}

int fake_getaddrinfo(const char *node, const char *service,
                     const struct addrinfo *hints, struct addrinfo **res) {
    sleep_for(seconds_in("FAKE_NETWORK_DELAY"));
    if (hints != NULL && hints->ai_family == AF_INET6) {
        sleep_for(seconds_in("FAKE_NETWORK_IPV6_DELAY"));
    }
    const getaddrinfo_function real_getaddrinfo =
        (getaddrinfo_function)dlsym(RTLD_NEXT, "getaddrinfo");
    if (!has_suffix(node, ".test")) {
        return real_getaddrinfo(node, service, hints, res);
    }
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const char *addresses = getenv("FAKE_NETWORK_ADDRESSES");
    char *nodes = strdup(addresses == NULL ? "" : addresses);
    if (nodes == NULL) {
        return EAI_MEMORY;
    }
    // freeaddrinfo() frees element by element, so the lists can be chained.
    struct addrinfo *head = NULL;
    struct addrinfo **tail = &head;
    int rc = 0;
    char *rest = NULL;
    for (char *entry = strtok_r(nodes, ",", &rest); entry != NULL;
         entry = strtok_r(NULL, ",", &rest)) {
        struct addrinfo *found = NULL;
        rc = resolve_entry(real_getaddrinfo, entry, service, hints, &found);
        if (rc != 0) {
            break;
        }
        *tail = found;
        while (*tail != NULL) {
            tail = &(*tail)->ai_next;
        }
    }
    free(nodes);
    if (rc == 0 && head == NULL) {
        rc = EAI_NODATA;  // like for a name without addresses of the family
    }
    if (rc != 0) {
        freeaddrinfo(head);
        return rc;
    }
    *res = head;
    return 0;
}

// The calls in the log, see FAKE_NETWORK_LOG.
enum { logged_poll = 0, logged_connect = 1 };

struct logged_call {
    int call;
    int value;  // the timeout of a poll()
};

// Appends a record of the call to the log, if asked to.
static void log_call(int call, int value) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    const char *path = getenv("FAKE_NETWORK_LOG");
    if (path == NULL) {
        return;
    }
    const mode_t mode = 0644;
    const int fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, mode);
    if (fd == -1) {
        return;
    }
    const struct logged_call record = {.call = call, .value = value};
    const ssize_t written = write(fd, &record, sizeof(record));
    (void)written;
    close(fd);
}

// Logs, remembers the socket of a slow connect(), and connects.
int fake_connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    log_call(logged_connect, 0);
    const long started = atomic_fetch_add(&connects_started, 1) + 1;
    if (started == number_in("FAKE_NETWORK_SLOW_CONNECT")) {
        atomic_store(&slow_socket, sockfd);
    }
    const connect_function real_connect =
        (connect_function)dlsym(RTLD_NEXT, "connect");
    return real_connect(sockfd, addr, addrlen);
}

// Logs and polls, hiding a slow socket as a negative fd, which poll() ignores.
int fake_poll(struct pollfd *fds, nfds_t nfds, int timeout) {
    log_call(logged_poll, timeout);
    const poll_function real_poll = (poll_function)dlsym(RTLD_NEXT, "poll");
    const long slow_connect = number_in("FAKE_NETWORK_SLOW_CONNECT");
    const int slow =
        slow_connect != 0 && atomic_load(&connects_started) == slow_connect
            ? atomic_load(&slow_socket)
            : -1;
    for (nfds_t i = 0; i < nfds; i++) {
        if (slow != -1 && fds[i].fd == slow) {
            fds[i].fd = ~slow;
        }
    }
    const int ready = real_poll(fds, nfds, timeout);
    for (nfds_t i = 0; i < nfds; i++) {
        if (slow != -1 && fds[i].fd == ~slow) {
            fds[i].fd = slow;
        }
    }
    return ready;
}
