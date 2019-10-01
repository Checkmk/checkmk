//
// test-tools.cpp :

#include "pch.h"

#include "test_tools.h"

#include "algorithm"  // for remove_if
#include "cfg.h"
#include "corecrt_terminate.h"  // for terminate
#include "exception"            // for terminate
#include "tools/_misc.h"
#include "tools/_tgt.h"          // for IsDebug
#include "yaml-cpp/emitter.h"    // for Emitter
#include "yaml-cpp/node/emit.h"  // for operator<<
#include "yaml-cpp/node/node.h"  // for Node

namespace tst {

void PrintNode(YAML::Node node, std::string_view S) {
    if (tgt::IsDebug()) {
        YAML::Emitter emit;
        emit << node;
        XLOG::l("{}:\n{}", S, emit.c_str());
    }
}

void SafeCleanTempDir() {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto really_temp_dir = temp_dir.find(L"\\tmp", 0) != std::wstring::npos;
    if (!really_temp_dir) return;

    // clean
    fs::remove_all(cma::cfg::GetTempDir());
    fs::create_directory(temp_dir);
}

void SafeCleanTmpxDir() {
    namespace fs = std::filesystem;
    if (very_temp != "tmpx") {
        XLOG::l.crit(
            "Recursive folder remove is allowed only for very temporary folders");
        std::terminate();
        return;
    }

    // clean
    fs::remove_all(very_temp);
}

void SafeCleanTempDir(std::string_view sub_dir) {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto really_temp_dir = temp_dir.find(L"\\tmp", 0) != std::wstring::npos;
    if (!really_temp_dir) {
        XLOG::l("attempt to delete suspicious dir {}",
                wtools::ConvertToUTF8(temp_dir));
        return;
    }

    // clean
    fs::path t_d = temp_dir;
    fs::remove_all(t_d / sub_dir);
    fs::create_directory(t_d / sub_dir);
}

template <typename T, typename V>
void RemoveElement(T& Container, const V& Str) {
    Container.erase(std::remove_if(Container.begin(), Container.end(),
                                   [Str](const std::string& Candidate) {
                                       return cma::tools::IsEqual(Str,
                                                                  Candidate);
                                   }),
                    Container.end());
}

void EnableSectionsNode(const std::string_view& Str, bool UpdateGlobal) {
    using namespace cma::cfg;

    auto enabled = GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);

    // add section name to internal array if not found
    if (std::end(enabled) == std::find(enabled.begin(), enabled.end(), Str)) {
        enabled.emplace_back(Str);
        PutInternalArray(groups::kGlobal, vars::kSectionsEnabled, enabled);
    }

    // pattern to remove INternalArray element
    auto disabled = GetInternalArray(groups::kGlobal, vars::kSectionsDisabled);
    RemoveElement(disabled, Str);
    PutInternalArray(groups::kGlobal, vars::kSectionsDisabled, disabled);

    if (UpdateGlobal) groups::global.loadFromMainConfig();
}
std::vector<std::string> ReadFileAsTable(const std::string& Name) {
    std::ifstream in(Name.c_str());
    std::stringstream sstr;
    sstr << in.rdbuf();
    auto content = sstr.str();
    return cma::tools::SplitString(content, "\n");
}

}  // namespace tst
