
// provides basic api to start and stop service
#include "stdafx.h"

#include <shlobj.h>
#include <userenv.h>

#include <string>

#include "tools/_process.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "logger.h"
#include "service_api.h"

namespace cma {

namespace install {

std::wstring FindMsiExec() {
    using namespace cma::tools;
    static std::wstring path_to_msiexec;
    static std::wstring msiexe;
    if (path_to_msiexec.empty()) {
        path_to_msiexec = win::GetSystem32Folder();
    }

    if (!msiexe.empty()) return msiexe;

    if (IsFileExist(path_to_msiexec + L"\\msiexec.exe")) {
        return path_to_msiexec + L"\\msiexec.exe";
    }

    XLOG::l("Path to msiexec not found");
    return {};

}  // namespace srv

std::wstring MakeTempFileNameInTempPath(const std::wstring &Name) {
    // Find Temporary Folder
    auto temp_folder = cma::tools::win::GetTempFolder();
    if (temp_folder.empty()) {
        xlog::l("Updating is NOT possible, temporary folder not found\n")
            .print();
        return {};
    }

    // #TODO make Function

    return temp_folder + Name;
}

// check that update exists and exec it
// returns true when update found and ready to exec
bool CheckForUpdateFile(const std::wstring Name, const std::wstring Path,
                        UpdateType Update, bool StartUpdateProcess) {
    // find path to msiexec, in Windows it is in System32 folder
    const auto exe = FindMsiExec();
    if (exe.empty()) return false;

    // check file existence
    std::wstring msi_base = Path + L"\\" + Name;
    if (!cma::tools::IsFileExist(msi_base)) return false;

    switch (Update) {
        case kMsiExec:
        case kMsiExecQuiet:
            break;
        default:
            xlog::l("Invalid Option %d", Update).print();
            return false;
    }

    // Move file to temporary folder
    auto msi_to_install = MakeTempFileNameInTempPath(Name);
    if (msi_to_install.empty()) return false;

    if (cma::tools::IsFileExist(msi_to_install)) {
        auto ret = ::DeleteFile(msi_to_install.c_str());
        if (!ret) {
            xlog::l(
                "Updating is NOT possible, can't delete file %ls, error %d\n",
                msi_to_install.c_str(), GetLastError())
                .print();
            return false;
        }
    }

    // actual move
    auto ret = ::MoveFile(msi_base.c_str(), msi_to_install.c_str());
    if (!ret) {
        xlog::l("Updating is NOT possible, can't move file, error %d\n",
                GetLastError())
            .print();
        return false;
    }

    // Prepare Command
    std::wstring command = exe + L" ";
    command = command + L" /i " + msi_to_install +
              L" REINSTALL=ALL REINSTALLMODE=amus ";

    if (Update == kMsiExecQuiet)  // this is only normal method
        command += L" /quiet";    // but MS doesn't care at all :)

    XLOG::l("File {} exists\n Command is {}",
            wtools::ConvertToUTF8(msi_to_install.c_str()),
            wtools::ConvertToUTF8(command.c_str()));

    if (!StartUpdateProcess) {
        XLOG::l.w("Actual Updating is disabled");
        return true;
    }
    return cma::tools::RunStdCommand(command, false, TRUE);
}  // namespace srv

std::wstring GetMsiUpdateDirectory() {
    // read from config or preset during development
    //
    return cma::tools::win::GetSystem32Folder();
}

}  // namespace install
};  // namespace cma
