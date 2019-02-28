
// tools to control starting operations

#pragma once

namespace cma {

enum StartTypes { kDefault = 99, kService = 0, kTest, kExe };

StartTypes AppDefaultType();  // defined by main

// must be called on start
bool OnStart(StartTypes Type = kDefault, bool UpdateCacheOnSuccess = false,
             std::wstring ConfigFile = L"");

inline bool OnStartApp(bool UpdateCacheOnSuccess = true) {
    return OnStart(kDefault, UpdateCacheOnSuccess);
}

inline bool OnStartTest(bool UpdateCacheOnSuccess = false) {
    return OnStart(kTest, false);
}

// recommended to be called on exit. BUT, PLEASE WAIT FOR ALL THREADS/ ASYNC
void OnExit();  // #VIP will stop WMI and all services(in the future)

bool ConfigLoaded();

}  // namespace cma
