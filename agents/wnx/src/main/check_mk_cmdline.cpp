//
// check_mk_cmdline.cpp : This file contains ONLY cmdlines for the 'main'
//
// Precompiled
#include "pch.h"

#include "check_mk_cmdline.h"

#include <fmt/format.h>

#include <filesystem>
#include <functional>
#include <string>
#include <string_view>

#include "file_encryption.h"
#include "logger.h"
namespace cma::cmdline {

static std::pair<std::filesystem::path, std::filesystem::path>
GetFilenamesFromArg(int argc, const wchar_t **argv) {
    if (argc == 3) return {argv[2], argv[2]};
    if (argc > 3) return {argv[2], argv[3]};
    return {};
}

using FileProcessorFunc = std::function<bool(const std::filesystem::path &,
                                             const std::filesystem::path &)>;

static auto encode_l = [](const std::filesystem::path file_in,
                          const std::filesystem::path file_out) -> bool {
    using namespace cma;
    return encrypt::OnFile::Encode(encrypt::kObfuscateWord, file_in, file_out);
};

auto decode_cpp_l = [](const std::filesystem::path file_in,
                       const std::filesystem::path file_out) -> bool {
    using namespace cma;
    return encrypt::OnFile::Decode(encrypt::kObfuscateWord, file_in, file_out,
                                   encrypt::SourceType::cpp);
};

auto decode_python_l = [](const std::filesystem::path file_in,
                          const std::filesystem::path file_out) -> bool {
    using namespace cma;
    return encrypt::OnFile::Decode(encrypt::kObfuscateWord, file_in, file_out,
                                   encrypt::SourceType::python);
};

std::tuple<bool, int> HiddenCommandProcessor(int argc, const wchar_t **argv) {
    namespace fs = std::filesystem;

    if (argc <= 1) return {false, 0};

    std::wstring cmd = argv[1];
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::SendStringToStdio("\tAnalyzing...\n", XLOG::Colors::white);

    FileProcessorFunc fpf = nullptr;

    std::string log_type;

    if (cmd == kHiddenCommandEncrypt) {
        fpf = encode_l;
        log_type = "encrypting";
    } else if (cmd == kHiddenCommandDecryptCpp) {
        fpf = decode_cpp_l;
        log_type = "decrypting[cpp]";
    } else if (cmd == kHiddenCommandDecryptPython) {
        fpf = decode_python_l;
        log_type = "decrypting[python]";
    }

    if (fpf) {
        XLOG::SendStringToStdio(fmt::format("\tStarting {} ...\n", log_type),
                                XLOG::Colors::white);
        auto [file_in, file_out] = GetFilenamesFromArg(argc, argv);
        if (file_in.empty() || file_out.empty()) {
            XLOG::SendStringToStdio("\tParsing failed\n", XLOG::Colors::red);
            return {false, 0};
        }
        auto ret = fpf(file_in, file_out);

        auto result_string = fmt::format(
            "\t...{}, input file '{}', output file '{}'\n", log_type,
            ret ? "success" : "false", file_in.u8string(), file_out.u8string());
        XLOG::SendStringToStdio(result_string,
                                ret ? XLOG::Colors::white : XLOG::Colors::red);
        return {true, ret ? 0 : 9};
    }
    return {false, 0};
}

}  // namespace cma::cmdline
