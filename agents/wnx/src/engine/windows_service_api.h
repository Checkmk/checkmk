
// provides basic api to start and stop service

#pragma once
#ifndef windows_service_api_h__
#define windows_service_api_h__
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <chrono>
#include <cstdint>  // wchar_t when compiler options set weird
#include <functional>

#include "common/wtools_service.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

// Common Namespace for whole Windows Agent
namespace cma {

// Related to Service Agent Logic
namespace srv {
enum class StdioLog { no, yes, extended };
enum class FwMode { show, configure, clear };
class ServiceProcessor;
int InstallMainService();               // on install
int RemoveMainService();                // on remove
int TestIo();                           // on check -io
int TestMt();                           // on check -mt
int TestMainServiceSelf(int Interval);  // on check self
int TestLegacy();                       // on test
int RestoreWATOConfig();                // on restore
int ExecFirewall(srv::FwMode fw_mode, std::wstring_view app_name,
                 std::wstring_view name);  // on fw
int ExecMainService(StdioLog stdio_log);   // on exec
int ExecStartLegacy();                     // on start_legacy
int ExecStopLegacy();                      // on stop_legacy
int ExecCap();                             // on cap
int ExecVersion();                         // on version
int ExecPatchHash();                       // on patch_hash
int ExecShowConfig(std::string_view sec);  // on showconfig
int ExecUpgradeParam(bool Force);          // om upgrade

int ExecSkypeTest();  // on skype :hidden
int ExecResetOhm();   // on resetohm :hidden

int ExecReloadConfig();
int ExecUninstallAlert();
int ExecRemoveLegacyAgent();
void ExecUninstallClean();

int ExecRealtimeTest(bool Print);  // on rt
int ExecCvtIniYaml(std::filesystem::path IniFile,
                   std::filesystem::path YamlFile,
                   StdioLog stdio_log);  // on cvt
int ExecExtractCap(std::wstring_view cap_file,
                   std::wstring_view to);  //
int ExecSection(const std::wstring& SecName,
                int RepeatPause,      // if 0 no repeat
                StdioLog stdio_log);  // on section
int ServiceAsService(std::wstring_view app_name,
                     std::chrono::milliseconds Delay,
                     std::function<bool(const void* Processor)>
                         InternalCallback) noexcept;  // service execution

void ProcessFirewallConfiguration(std::wstring_view app_name);
[[maybe_unused]] bool ProcessServiceConfiguration(std::wstring_view app_name);

// Converter API from YML language to wtools
wtools::WinService::ErrorMode GetServiceErrorModeFromCfg(std::string_view text);
wtools::WinService::StartMode GetServiceStartModeFromCfg(std::string_view text);

// NAMES
constexpr const wchar_t* kServiceName = L"CheckMkService";
constexpr const wchar_t* kServiceDisplayName =
    L"Check MK windows agent service";

// PARAMETERS
constexpr int kServiceStartType = SERVICE_DEMAND_START;  //  SERVICE_AUTO_START;
constexpr const wchar_t* kServiceDependencies = L"";
constexpr const wchar_t* kServiceAccount = L"NT AUTHORITY\\LocalService";
constexpr const wchar_t* kServicePassword = nullptr;

constexpr std::wstring_view kSrvFirewallRuleName = L"CheckMk Service Rule";
constexpr std::wstring_view kAppFirewallRuleName = L"CheckMk Application Rule";

// service configuration
// main call
// sets service to restart on error.
void SelfConfigure();
// secondary API calls
SC_HANDLE SelfOpen();
bool IsServiceConfigured(SC_HANDLE handle);
bool ConfigureServiceAsRestartable(SC_HANDLE handle);

bool IsGlobalStopSignaled();

}  // namespace srv
};  // namespace cma

#endif  // windows_service_api_h__
