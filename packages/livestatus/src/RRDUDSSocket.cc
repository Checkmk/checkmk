// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDUDSSocket.h"

#include <sys/socket.h>
#include <sys/un.h>

#include <algorithm>
#include <array>
#include <utility>

#include "livestatus/Logger.h"
#include "livestatus/POSIXUtils.h"
#include "livestatus/StringUtils.h"

RRDUDSSocket::RRDUDSSocket(std::filesystem::path path, Logger *logger,
                           verbosity v)
    : path_{std::move(path)}, logger_{logger}, verbosity_{v} {}

RRDUDSSocket::~RRDUDSSocket() { close(); }

void RRDUDSSocket::connect() {
    const int sock = ::socket(PF_UNIX, SOCK_STREAM, 0);
    if (sock == -1) {
        throw generic_error{"cannot create socket"};
    }

    struct sockaddr_un sockaddr{.sun_family = AF_UNIX, .sun_path = ""};
    path_.string().copy(&sockaddr.sun_path[0], sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    if (::connect(sock, reinterpret_cast<const struct sockaddr *>(&sockaddr),
                  sizeof(sockaddr)) == -1) {
        throw generic_error{"cannot connect"};
    }

    if (verbosity_ == verbosity::full) {
        Notice(logger()) << "successfully connected";
    }
    socket_ = sock;
    file_ = fdopen(sock, "r");
}

std::string RRDUDSSocket::readLine() const {
    // NOLINTNEXTLINE(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays)
    char answer[512];
    // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-array-to-pointer-decay)
    if (fgets(answer, sizeof(answer), file_) == nullptr) {
        throw generic_error("cannot read reply");
    }
    // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-array-to-pointer-decay)
    return mk::rstrip(answer);
}

std::string RRDUDSSocket::read(std::size_t count) const {
    std::array<char, 512> answer{};
    // NOLINTBEGIN(cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-pointer-arithmetic)
    const auto rd = ::fread(answer.data(), sizeof(decltype(answer)::value_type),
                            std::min(count, answer.size()), file_);
    if (feof(file_) != 0 || ferror(file_) != 0) {
        throw generic_error("cannot read reply");
    }
    return {answer.begin(), answer.begin() + rd};
    // NOLINTEND(cppcoreguidelines-pro-bounds-array-to-pointer-decay,cppcoreguidelines-pro-bounds-pointer-arithmetic)
}

ssize_t RRDUDSSocket::write(std::string_view text,
                            std::chrono::milliseconds timeout) const {
    if (!isConnected()) {
        return 0;
    }
    return writeWithTimeout(socket_, text, timeout);
}

void RRDUDSSocket::close() {
    if (!isConnected()) {
        return;
    }
    if (verbosity_ == verbosity::full) {
        Notice(logger()) << "closing connection";
    }
    // NOLINTNEXTLINE(cppcoreguidelines-owning-memory)
    (void)::fclose(file_);
    socket_ = -1;
    file_ = nullptr;
}
