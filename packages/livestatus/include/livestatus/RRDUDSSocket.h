// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDUDSSocket_h
#define RRDUDSSocket_h

#include <sys/types.h>

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <string>
#include <string_view>

class Logger;

class RRDUDSSocket {
public:
    enum class verbosity { none, full };
    RRDUDSSocket(std::filesystem::path path, Logger *logger, verbosity v);
    ~RRDUDSSocket();
    void connect();
    [[nodiscard]] Logger *logger() const { return logger_; }
    [[nodiscard]] std::string readLine() const;
    [[nodiscard]] std::string read(std::size_t count) const;
    [[nodiscard]] ssize_t write(std::string_view text,
                                std::chrono::milliseconds timeout) const;
    [[nodiscard]] bool isConnected() const { return socket_ != -1; }
    void close();

private:
    std::filesystem::path path_;
    mutable Logger *logger_;
    int socket_{-1};
    FILE *file_{nullptr};
    verbosity verbosity_;
};

#endif
