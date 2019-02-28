#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <vector>

#include "tools/_xlog.h"

#include "logger.h"

namespace cma::tools {

// more or less tested indirectly with test-player
template <typename T>
std::optional<std::vector<uint8_t>> ReadFileInVector(
    const T* FileName) noexcept {
    try {
#if defined(_MSC_BUILD)
        std::ifstream f(FileName, std::ios::binary);
#else
        // GCC can't wchar, conversion required
        std::basic_string<T> str(FileName);
        std::string file_name(str.begin(), str.end());
        std::ifstream f(file_name, std::ios::binary);
#endif

        if (!f.good()) {
            std::string fname;
            for (int i = 0;; i++) {
                auto ch = static_cast<char>(FileName[i]);
                fname += ch;
                if (!ch) break;
            }
            char dir[MAX_PATH * 2] = "";
            GetCurrentDirectoryA(MAX_PATH * 2, dir);
            xlog::l("File not %s found in %s", fname.c_str(), dir);
            return {};
        }

        // size obtain
        f.seekg(0, std::ios::end);
        auto fsize = static_cast<uint32_t>(f.tellg());

        // buffer obtain
        uint8_t* buffer = nullptr;
        buffer = new uint8_t[fsize];
        ON_OUT_OF_SCOPE(delete[] buffer);

        // read contents
        f.seekg(0, std::ios::beg);
        f.read(reinterpret_cast<char*>(buffer), fsize);

        f.close();  // normally not required, closed automatically

        std::vector<uint8_t> v;
        v.reserve(fsize);

        v.assign(buffer, buffer + fsize);

        return v;
    } catch (const std::exception& e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        xlog::l(XLOG_FUNC + "Exception %s generated", e.what());
        return {};
    }
    return {};
}

inline std::optional<std::vector<uint8_t>> ReadFileInVector(
    const std::filesystem::path& File) noexcept {
    if (File.u8string().empty()) return {};

    return ReadFileInVector(File.u8string().c_str());
}

}  // namespace cma::tools
