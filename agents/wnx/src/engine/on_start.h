
// tools to control starting operations

#pragma once

namespace cma {

enum class AppType { automatic = 99, srv = 0, test, exe };
enum class YamlCacheOp { nothing, update };
constexpr const wchar_t* kTemporaryRoot = L"CMA_TEST_DIR";

AppType AppDefaultType();  // defined by main

// must be called on start
bool OnStart(AppType Type = AppType::automatic,
             YamlCacheOp UpdateCacheOnSuccess = YamlCacheOp::nothing,
             const std::wstring& ConfigFile = L"");

inline bool OnStartApp(YamlCacheOp UpdateCacheOnSuccess = YamlCacheOp::update) {
    return OnStart(AppType::automatic, UpdateCacheOnSuccess);
}

inline bool OnStartTest(
    YamlCacheOp UpdateCacheOnSuccess = YamlCacheOp::nothing) {
    return OnStart(AppType::test, UpdateCacheOnSuccess);
}

// recommended to be called on exit. BUT, PLEASE WAIT FOR ALL THREADS/ ASYNC
void OnExit();  // #VIP will stop WMI and all services(in the future)

bool ConfigLoaded();

}  // namespace cma
