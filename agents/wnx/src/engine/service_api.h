
// provides basic api to start and stop service

#pragma once
#ifndef service_api_h__
#define service_api_h__

#include <string>
namespace cma {

namespace install {
enum UpdateType { kMsiExec, kMsiExecQuiet };
constexpr const wchar_t* const kDefaultMsiFileName = L"check_mk_service.msi";

std::wstring GetMsiUpdateDirectory();

// StartUpdateProcess == false when we only testing functionality
bool CheckForUpdateFile(const std::wstring Name, const std::wstring Path,
                        UpdateType Update, bool StartUpdateProcess);
std::wstring FindMsiExec();
std::wstring MakeTempFileNameInTempPath(const std::wstring& Name);

}  // namespace install

};  // namespace cma

#endif  // service_api_h__
