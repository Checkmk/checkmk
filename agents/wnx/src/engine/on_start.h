
// tools to control starting operations

#pragma once
#include <filesystem>
#include <string>
#include <string_view>

namespace cma {

enum class AppType { automatic = 99, srv = 0, test, exe, failed };
enum class YamlCacheOp { nothing, update };
constexpr const wchar_t* kTemporaryRoot = L"CMA_TEST_DIR";
constexpr const wchar_t* kRemoteMachine = L"REMOTE_MACHINE";
constexpr const wchar_t* kAutoReload = L"CMA_AUTO_RELOAD";

AppType AppDefaultType();  // defined by main

// must be called on start
bool OnStart(AppType Type = AppType::automatic,
             const std::wstring& ConfigFile = L"");

bool LoadConfig(AppType Type, const std::wstring& ConfigFile);
bool ReloadConfig();
inline bool OnStartApp() { return OnStart(AppType::automatic); }

inline bool OnStartTest() { return OnStart(AppType::test); }

// recommended to be called on exit. BUT, PLEASE WAIT FOR ALL THREADS/ ASYNC
void OnExit();  // #VIP will stop WMI and all services(in the future)

bool ConfigLoaded();

class UninstallAlert {
public:
    UninstallAlert() = default;
    UninstallAlert(const UninstallAlert&) = delete;
    UninstallAlert(UninstallAlert&&) = delete;
    UninstallAlert& operator=(const UninstallAlert&) = delete;
    UninstallAlert& operator=(UninstallAlert&&) = delete;
    bool isSet() const noexcept {
        return set_;
    }                       // check during exit from the service
    void clear() noexcept;  // test only
    void set() noexcept;    // set when command is got from the
                            // transport
private:
    bool set_ = false;
};

extern UninstallAlert G_UninstallALert;

std::pair<std::filesystem::path, std::filesystem::path> FindAlternateDirs(
    std::wstring_view environment_variable);

}  // namespace cma
