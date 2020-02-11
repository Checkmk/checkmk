
#include "stdafx.h"

#include "file_encryption.h"

#include <fmt/format.h>

#include <string>
#include <string_view>

#include "cma_core.h"
#include "glob_match.h"
#include "logger.h"

namespace cma::encrypt {
static std::unique_ptr<Commander> MakeInternalCrypt(const std::string& p) {
    return std::make_unique<Commander>(p);
}

static bool WriteDataToFile(const std::filesystem::path& name,
                            const std::vector<char>& buffer) {
    std::ofstream ofd(name, std::ios::binary | std ::ios::trunc);
    auto marker = fmt::format("{}{:04}", kObfuscateMark, buffer.size());
    if (ofd.good() && ofd.write(buffer.data(), buffer.size()).good()) {
        XLOG::l.t("Data saved in '{}'", name.u8string());
        return true;
    }

    XLOG::l.t("'{}' is bad", name.u8string());

    return false;
}

bool OnFile::Encode(std::string_view password,
                    const std::filesystem::path& name) {
    return Encode(password, name, name);
}

bool OnFile::Decode(std::string_view password,
                    const std::filesystem::path& name, SourceType type) {
    return Decode(password, name, name, type);
}

bool OnFile::Encode(std::string_view password,
                    const std::filesystem::path& name,
                    const std::filesystem::path& name_out) {
    if (password.empty()) {
        XLOG::l.w("Password is empty, encryption is impossible");
        return false;
    }

    auto result = std::move(ReadFullFile(name));
    if (result.empty()) {
        XLOG::l.w("File '{}' is empty, encryption is impossible",
                  name.u8string());
        return false;
    }
    auto c = MakeInternalCrypt(std::string(password));
    auto block_size = c->blockSize();
    auto data_size = result.size();
    if (block_size.has_value()) {
        auto sz = result.size();
        auto b_size = *block_size / 8;
        sz = ((sz / b_size) + 1) * b_size;
        result.resize(sz);
        memset(&result[data_size], ' ', sz - data_size);
    }

    auto [success, write_size] =
        c->encode(result.data(), data_size, result.size(), true);

    if (!success) {
        XLOG::l.w("Can't encrypt '{}'", name.u8string());
        return false;
    }

    result.resize(write_size);
    result.insert(result.end(), kObfuscateMark.data(),
                  kObfuscateMark.data() + 4);
    auto count = fmt::format("{:08}", data_size);
    result.insert(result.end(), count.data(), count.data() + 8);
    return WriteDataToFile(name_out, result);
}

bool OnFile::IsEncodedBuffer(const std::vector<char>& result,
                             std::string_view name) {
    if (result.empty()) {
        XLOG::d.i("File '{}' is empty, decryption is impossible", name);
        return false;
    }
    auto data_size = result.size();
    if (data_size < kObfuscatedSuffixSize) {
        XLOG::d.i("File '{}' is too short", name);
        return false;
    }

    auto marker = std::string_view(&result[data_size - kObfuscatedSuffixSize],
                                   kObfuscatedWordSize);
    if (marker != kObfuscateMark) {
        XLOG::d.i("File '{}' is not encrypted", name, marker);
        return false;
    }

    return true;
}

bool OnFile::DecodeBuffer(std::string_view password, std::vector<char>& result,
                          SourceType type, std::string_view name) {
    if (!IsEncodedBuffer(result, name)) {
        XLOG::d.w("File '{}' is not encoded", name);
        return false;
    }

    auto data_size = result.size();
    if (data_size < kObfuscatedSuffixSize) {
        XLOG::l("File '{}' is too short", name);
        return false;
    }

    auto length_sv = std::string_view(
        &result[data_size - kObfuscatedLengthSize], kObfuscatedLengthSize);
    try {
        auto length = std::stoi(std::string(length_sv));

        auto c = MakeInternalCrypt(std::string(password));
        auto [success, sz] = c->decode(
            result.data(), data_size - kObfuscatedSuffixSize,
            type == SourceType::cpp);  // false: python doesn't close the block

        if (!success) {
            XLOG::l.w("Can't decrypt '{}'", name);
            return false;
        }

        if (type == SourceType::python) sz = length;

        result.resize(sz);
    } catch (const std::exception& e) {
        XLOG::l.w("Exception '{}' during decrypt '{}'", e.what(), name);
        return false;
    }

    return true;
}

bool OnFile::Decode(const std::string_view password,
                    const std::filesystem::path& name,
                    const std::filesystem::path& name_out, SourceType type

) {
    if (password.empty()) {
        XLOG::l.w("Password is empty, encryption is impossible");
        return false;
    }

    auto result = std::move(ReadFullFile(name));
    if (!DecodeBuffer(password, result, type, name.u8string())) return false;

    return WriteDataToFile(name_out, result);
}

static PathVector GatherMatchingFiles(
    const std::filesystem::path& search_dir,
    std::wstring_view fname_pattern) noexcept {
    namespace fs = std::filesystem;
    PathVector paths;

    std::wstring pattern(fname_pattern);
    try {
        for (const auto& entry : fs::recursive_directory_iterator(
                 search_dir, fs::directory_options::skip_permission_denied)) {
            // Found files must match the entire path pattern.
            std::error_code ec;
            auto status = entry.status(ec);
            auto entry_name = entry.path();
            if (ec) {
                XLOG::t("Access to {} is not possible, status {}",
                        entry_name.u8string(), ec.value());
                continue;
            }

            if (!fs::is_regular_file(status)) continue;

            // normal file
            if (cma::tools::GlobMatch(pattern, entry_name.wstring())) {
                paths.push_back(entry);
            }
        }
        return paths;
    } catch (std::exception& e) {
        XLOG::l("Exception recursive {}", e.what());
    } catch (...) {
        XLOG::l("Exception recursive");
    }

    return {};
}

int OnFile::DecodeAll(const std::filesystem::path& dir, std::wstring_view mask,
                      SourceType type) {
    auto paths = GatherMatchingFiles(dir, mask);
    if (paths.empty()) return 0;
    int count = 0;
    for (auto& p : paths) {
        auto ret = Decode(kObfuscateWord, p, type);
        if (ret) ++count;
    }

    return count;
}

std::vector<char> OnFile::ReadFullFile(const std::filesystem::path& name) {
    try {
        std::ifstream ifd(name.u8string(), std::ios::binary | std::ios::ate);
        auto size = static_cast<int>(ifd.tellg());
        if (size == -1) {
            XLOG::l("Can't read file '{}', error is {}", name.u8string(),
                    ::GetLastError());
            return {};
        }
        ifd.seekg(0, std::ios::beg);
        std::vector<char> buffer;
        buffer.resize(size);  // << resize not reserve
        ifd.read(buffer.data(), size);
        return buffer;
    } catch (const std::exception& e) {
        XLOG::l("Exception reading the file '{}', error is {}", name.u8string(),
                e.what());
        return {};
    }
}

}  // namespace cma::encrypt
