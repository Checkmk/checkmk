
// provides basic api to start and stop service
#include "stdafx.h"

#include <shlobj.h>
#include <userenv.h>

#include <filesystem>
#include <string>

#include "tools/_process.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "logger.h"
#include "service_api.h"

#include "cfg.h"

namespace cma {

namespace install {

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
    const auto exe = cma::cfg::GetMsiExecPath();
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
    namespace fs = std::filesystem;

    return cma::cfg::GetUpdateDir();
}

}  // namespace install
};  // namespace cma
