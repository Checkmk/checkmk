#ifndef test_tools_h__
#define test_tools_h__
//
#include <filesystem>
#include <string>
#include <tuple>

#include "cfg.h"

namespace tst {
class YamlLoader {
public:
    YamlLoader() {
        using namespace cma::cfg;
        std::error_code ec;
        std::filesystem::remove(cma::cfg::GetBakeryFile(), ec);
        cma::OnStart(cma::kTest);

        auto yaml = GetLoadedConfig();
        ProcessKnownConfigGroups();
        SetupEnvironmentFromGroups();
    }
    ~YamlLoader() { OnStart(cma::kTest); }
};

inline void CreateFile(std::filesystem::path Path, std::string Content) {
    std::ofstream ofs(Path);

    ofs << Content;
}

void SafeCleanTempDir();
void SafeCleanTempDir(const std::string Sub);

inline auto CreateIniFile(std::filesystem::path Lwa, const std::string Content,
                          const std::string YamlName) {
    auto ini_file = Lwa / (YamlName + ".ini");
    CreateFile(Lwa / ini_file, Content);
    return ini_file;
}

inline std::tuple<std::filesystem::path, std::filesystem::path> CreateInOut() {
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    auto normal_dir =
        temp_dir.wstring().find(L"\\temp", 0) != std::wstring::npos;
    if (normal_dir) {
        std::error_code ec;
        auto lwa_dir = temp_dir / "in";
        auto pd_dir = temp_dir / "out";
        fs::create_directories(lwa_dir, ec);
        fs::create_directories(pd_dir, ec);
        return {lwa_dir, pd_dir};
    }
    return {};
}

// add Str to enabled sections and remove from disabled
// optionally updates parameters in Config
void EnableSectionsNode(const std::string_view& Str, bool UpdateGlobal = true);

inline void SafeCleanBakeryDir() {
    namespace fs = std::filesystem;
    auto bakery_dir = cma::cfg::GetBakeryDir();
    auto normal_dir = bakery_dir.find(L"\\bakery", 0) != std::wstring::npos;
    if (normal_dir) {
        // clean
        fs::remove_all(bakery_dir);
        fs::create_directory(bakery_dir);
    } else {
        XLOG::l("attempt to delete suspicious dir {}",
                wtools::ConvertToUTF8(bakery_dir));
    }
}
}  // namespace tst
#endif  // test_tools_h__
