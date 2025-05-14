// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

/* This small helper program is intended to be installed SUID root.
   Otherwise it is pointless. It creates a UDP socket with port 514.
   This is a privileged operation. Then it drops the privileges,
   moves that port to file descriptor 3 and executes the mkeventd.

   That can then simply use filedescriptor 3 and receive syslog
   messages */

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

// Example command line:
// mkeventd_open514 --syslog --syslog-fd 3 --syslog-tcp --syslog-tcp-fd 4
// --snmptrap --snmptrap-fd 5

int bind_socket(int sock_type, const char* service) {
  addrinfo query{};
  query.ai_flags = AI_PASSIVE;
  query.ai_family = AF_UNSPEC;
  query.ai_socktype = sock_type;

  addrinfo *info = nullptr;
  if (::getaddrinfo(nullptr, service, &query, &info) != 0) {
    return -1;
  }

  int result = -1;

  for (addrinfo *curr = info; curr != nullptr; curr = curr->ai_next) {
    result = ::socket(curr->ai_family, curr->ai_socktype, 0);

    if (result != -1) {
      int optval = 1;
      if (::setsockopt(result, SOL_SOCKET, SO_REUSEADDR, &optval,
                       sizeof(optval)) != 0) {
        ::perror("Cannot set SO_REUSEADDR on socket inside mkeventd");
        ::exit(1);
      }

      if (::bind(result, curr->ai_addr, curr->ai_addrlen) == 0) {
        break;
      }
      ::close(result);
    }
  }

  ::freeaddrinfo(info);
  return result;
}

void open_socket_as_fd(int type, const char* service, int target_fd,
                       const char *error_message) {
  auto sock = bind_socket(type, service);

  if (sock == -1) {
    ::perror(error_message);
    ::exit(1);
  }

  // Make sure it is at the correct FD
  if (sock != target_fd) {
    ::dup2(sock, target_fd);
    ::close(sock);
  }
}

int main(int argc, char **argv) {
  int do_syslog = 0;
  int do_syslog_tcp = 0;
  int do_snmptrap = 0;

  int syslog_fd = -1;
  int syslog_tcp_fd = -1;
  int snmptrap_fd = -1;

  std::vector<std::string> arguments{argv, argv + argc};
  for (int i = 1; i < argc; i++) {
    if (arguments[i] == "--syslog") {
      do_syslog = 1;
    } else if (arguments[i] == "--syslog-tcp") {
      do_syslog_tcp = 1;
    } else if (arguments[i] == "--snmptrap") {
      do_snmptrap = 1;
    } else if (arguments[i] == "--syslog-fd") {
      syslog_fd = atoi(arguments[i + 1].c_str());
    } else if (arguments[i] == "--syslog-tcp-fd") {
      syslog_tcp_fd = atoi(arguments[i + 1].c_str());
    } else if (arguments[i] == "--snmptrap-fd") {
      snmptrap_fd = atoi(arguments[i + 1].c_str());
    }
  }

  // Syslog via UDP
  if (do_syslog != 0 && syslog_fd > 0) {
    open_socket_as_fd(
        SOCK_DGRAM, "syslog", syslog_fd,
        "Cannot bind UDP socket for syslog to port "
        "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the "
        "filesystem?)");
  }

  // Syslog via TCP
  if (do_syslog_tcp != 0 && syslog_tcp_fd > 0) {
    open_socket_as_fd(
        SOCK_STREAM, "syslog", syslog_tcp_fd,
        "Cannot bind UDP socket for syslog to port "
        "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the "
        "filesystem?)");
  }

  // SNMP traps
  if (do_snmptrap != 0 && snmptrap_fd > 0) {
    open_socket_as_fd(
        SOCK_DGRAM, "snmp-trap", snmptrap_fd,
        "Cannot bind UDP socket for snptrap to port "
        "(Is SUID bit set on mkeventd_open514? Is \"nosuid\" not set on the "
        "filesystem?)");
  }

  // Drop privileges
  if (getuid() != geteuid() && seteuid(getuid())) {
    perror("Cannot drop privileges");
    exit(1);
  }

  // Execute the actual program that needs access to the socket.
  ::execv((std::filesystem::path{argv[0]}.parent_path() / "mkeventd").c_str(),
          argv);
  perror("Cannot execute mkeventd");
}
