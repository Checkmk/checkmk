#ifndef test_tools_h__
#define test_tools_h__
//
#include <filesystem>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"

namespace tst {
class YamlLoader {
public:
    YamlLoader() {
        using namespace cma::cfg;
        std::error_code ec;
        std::filesystem::remove(cma::cfg::GetBakeryFile(), ec);
        cma::OnStart(cma::AppType::test);

        auto yaml = GetLoadedConfig();
        ProcessKnownConfigGroups();
        SetupEnvironmentFromGroups();
    }
    ~YamlLoader() { OnStart(cma::AppType::test); }
};

inline void ConstructFile(std::filesystem::path Path,
                          std::string_view Content) {
    std::ofstream ofs(Path);

    ofs << Content;
}

void SafeCleanTempDir();
void SafeCleanTempDir(std::string_view sub_dir);

inline auto CreateIniFile(std::filesystem::path Lwa, const std::string Content,
                          const std::string YamlName) {
    auto ini_file = Lwa / (YamlName + ".ini");
    ConstructFile(Lwa / ini_file, Content);
    return ini_file;
}

inline std::filesystem::path CreateWorkFile(const std::filesystem::path& Name,
                                            const std::string& Text) {
    namespace fs = std::filesystem;

    auto path = Name;

    std::ofstream ofs(path.u8string(), std::ios::binary);

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", path.u8string(), GetLastError());
        return {};
    }

    ofs << Text << "\n";
    return path;
}

inline std::tuple<std::filesystem::path, std::filesystem::path> CreateInOut() {
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    auto normal_dir =
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos;
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

const std::string_view very_temp = "tmpx";

void SafeCleanTmpxDir();

void PrintNode(YAML::Node node, std::string_view S);
}  // namespace tst
#endif  // test_tools_h__
