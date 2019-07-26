
// tools to control starting operations

#pragma once

namespace cma {

enum class AppType { automatic = 99, srv = 0, test, exe, failed };
enum class YamlCacheOp { nothing, update };
constexpr const wchar_t* kTemporaryRoot = L"CMA_TEST_DIR";
constexpr const wchar_t* kRemoteMachine = L"REMOTE_MACHINE";

AppType AppDefaultType();  // defined by main

// must be called on start
bool OnStart(AppType Type = AppType::automatic,
             const std::wstring& ConfigFile = L"");

inline bool OnStartApp() { return OnStart(AppType::automatic); }

inline bool OnStartTest() { return OnStart(AppType::test); }

// recommended to be called on exit. BUT, PLEASE WAIT FOR ALL THREADS/ ASYNC
void OnExit();  // #VIP will stop WMI and all services(in the future)

bool ConfigLoaded();

std::pair<std::filesystem::path, std::filesystem::path> FindAlternateDirs(
    std::wstring_view environment_variable);

}  // namespace cma
