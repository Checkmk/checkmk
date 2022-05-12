// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/agent_plugins.h"

#include <filesystem>

#include "cfg.h"
#include "common/wtools.h"
#include "tools/_misc.h"
namespace fs = std::filesystem;
using namespace std::string_literals;

namespace cma::provider {
namespace {
enum class FileType { ps1, cmd, vbs, py, other };

size_t GetLength(std::ifstream &ifs) {
    ifs.seekg(0, ifs.end);
    auto length = ifs.tellg();
    ifs.seekg(0, ifs.beg);
    return static_cast<size_t>(length);
}

std::string ReadFileToString(const fs::path &file) {
    std::string ret;
    std::ifstream ifs(file, std::ifstream::in);
    if (ifs) {
        auto length = GetLength(ifs);
        ret.resize(static_cast<size_t>(length));
        ifs.read(ret.data(), length);
        if (ifs.good() || ifs.eof()) {
            return ret;
        }
        XLOG::d("Can't read '{}'", file.u8string());
    } else {
        XLOG::d("Can't open '{}'", file.u8string());
    }
    return {};
}

std::string Marker(FileType file_type) {
    switch (file_type) {
        case FileType::cmd:
            return "set CMK_VERSION="s;
        case FileType::ps1:
            return "$CMK_VERSION = "s;
        case FileType::vbs:
            return "Const CMK_VERSION = "s;
        case FileType::py:
            return "__version__ = "s;
        case FileType::other:
            return {};
    }
    // unreachable
    return {};
}

std::string FindVersionInfo(const fs::path &file, FileType file_type) {
    try {
        std::string ret = ReadFileToString(file);
        auto marker = Marker(file_type);
        if (marker.empty()) {
            XLOG::t("This file type '{}' is not supported", file);
            return {};
        }
        const auto offset = ret.find(marker);
        if (offset == std::string::npos) {
            return fmt::format("{}:CMK_VERSION = unversioned", file);
        }
        const auto end = ret.find("\n", offset);
        if (end == std::string::npos) {
            XLOG::t("This file type '{}' strange!", file);
            return {};
        }
        auto version_text = ret.substr(offset + marker.length(),
                                       end - offset - marker.length());
        return fmt::format("{}:CMK_VERSION = {}", file, version_text);

    } catch (const std::exception &e) {
        XLOG::d("Can't access '{}', exception '{}'", file.u8string(), e.what());
    }
    return {};
}

std::vector<std::string> ScanDir(const fs::path dir) {
    std::vector<std::string> result;
    std::error_code ec;
    for (auto const &entry : fs::recursive_directory_iterator{dir, ec}) {
        if (fs::is_directory(entry, ec) || !fs::is_regular_file(entry, ec)) {
            continue;
        }
        auto file = entry.path();
        auto extension = file.extension().wstring();
        tools::WideLower(extension);
        std::string text;
        const std::unordered_map<std::wstring, FileType> map = {
            {L".ps1", FileType::ps1},
            {L".cmd", FileType::cmd},
            {L".bat", FileType::cmd},
            {L".vbs", FileType::vbs},
            {L".py", FileType::py},
        };
        auto type =
            map.contains(extension) ? map.at(extension) : FileType::other;
        auto version_text = FindVersionInfo(file, type);
        if (!version_text.empty()) {
            result.emplace_back(version_text);
        }
    }
    return result;
}
}  // namespace

std::string AgentPlugins::makeBody() {
    std::string out = section::MakeHeader(section::kAgentPlugins);
    out += fmt::format("pluginsdir {}\n",
                       wtools::ToUtf8(cfg::GetUserPluginsDir()));
    out += fmt::format("localdir {}\n", wtools::ToUtf8(cfg::GetLocalDir()));
    for (const auto &dir : {cfg::GetUserPluginsDir(), cfg::GetLocalDir()}) {
        auto data = ScanDir(dir);
        for (const auto &entry : data) {
            out += entry + "\n";
        }
    }
    out.pop_back();
    return out;
}
};  // namespace cma::provider
