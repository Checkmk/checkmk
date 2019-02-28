// SNIPPETS
// start app from service
// - from a user
// - as Yukko
#include <windows.h>

bool ToolRunApplicationInSession(const wchar_t *Command, ULONG Sessi onId,
                                 BOOL Console, BOOL WaitTillEnd) {
    if (!Command[0]) return false;

    // copy command line to new buffer since it will be modified inside
    // CreateProcessAsUserW
    auto const cmd = Command;
    //	wcscpy(cmd, (WCHAR*)Command);

    dump("New command line is :%ls\n", cmd);

    HANDLE hToken = NULL;
    BOOL ret = WTSQueryUserToken(SessionId, &hToken);
    if (!ret || !hToken) {
        dump("[error] Fail to WTSQueryUserToken, error:%d \n", GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(CloseHandle(hToken));

    void *pEnv = nullptr;
    auto ret = CreateEnvironmentBlock(&pEnv, hToken, FALSE);
    if (!ret || !pEnv) {
        xlog::l("[error] Fail to CreateEnvironmentBlock, error:%d \n",
                GetLastError());
        return FALSE;
    }
    ON_OUT_OF_SCOPE(DestroyEnvironmentBlock(pEnv););

    ret = ImpersonateLoggedOnUser(hToken);
    if (!ret) {
        xlog::l("[error] Fail to ImpersonateLoggedOnUser, error:%d \n",
                GetLastError());
        return false;
    }

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(STARTUPINFOW);
    si.lpDesktop = (LPWSTR)L"winsta0\\default";

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    // Start the process with CreateProcessAsUserW().
    DWORD creation_flag = NORMAL_PRIORITY_CLASS | CREATE_UNICODE_ENVIRONMENT;
    if (Console) creation_flag |= CREATE_NEW_CONSOLE;

    ret = ::CreateProcessAsUserw(hToken, NULL, (LPWSTR)cmd, NULL, NULL, TRUE, 0,
                                 pEnv, NULL, &si, &pi);
    if (ret) {
        if (WaitTillEnd) {
            ret = WaitForSingleObject(pi.hProcess, 5000);
            xlog::l("Waiting proc for end = %d\n", ret);
        }
        xlog::l("[success] CreateProcess, error:%ls \n", cmd);
    } else {
        xlog::l("[error] Fail to CreateProcessAsUserW, error:%d \n",
                GetLastError());
    }

    RevertToSelf();

    if (pi.hProcess) CloseHandle(pi.hProcess);
    if (pi.hThread) CloseHandle(pi.hThread);

    return true;
}

void ExternalCmd(const std::wstring &cmdline) {
    SECURITY_DESCRIPTOR security_descriptor;
    SECURITY_ATTRIBUTES security_attributes;
    // initialize security descriptor (Windows NT)
    InitializeSecurityDescriptor(&security_descriptor,
                                 SECURITY_DESCRIPTOR_REVISION);
    SetSecurityDescriptorDacl(&security_descriptor, true, nullptr, false);
    security_attributes.lpSecurityDescriptor = &security_descriptor;

    security_attributes.nLength = sizeof(SECURITY_ATTRIBUTES);
    // child process needs to be able to inherit the pipe handles
    security_attributes.bInheritHandle = true;

    /*
        std::tie(_stdout, _script_stdout) =
            createPipe(security_attributes, _winapi);

        if (_with_stderr) {
            std::tie(_stderr, _script_stderr) =
                createPipe(security_attributes, _winapi);
        }
    */

    // base new process statup info on current process
    STARTUPINFO si;
    std::memset(&si, 0, sizeof(STARTUPINFO));
    si.cb = sizeof(STARTUPINFO);
    GetStartupInfo(&si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    /*
        si.hStdOutput = _script_stdout.get();
        si.hStdError = _with_stderr ? _script_stdout.get() :
       _script_stderr.get();
    */

    bool detach_process = true;

    DWORD dwCreationFlags = CREATE_NEW_CONSOLE;
    if (detach_process) {
        dwCreationFlags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS;
    }

    PROCESS_INFORMATION pi;
    std::memset(&pi, 0, sizeof(PROCESS_INFORMATION));

    if (!::CreateProcess(nullptr, (LPWSTR)cmdline.c_str(), nullptr, nullptr,
                         TRUE, dwCreationFlags, nullptr, nullptr, &si, &pi)) {
        xlog::l("failed to spawn process %d", GetLastError());
    }
    if (pi.hProcess) CloseHandle(pi.hProcess);
    if (pi.hThread) CloseHandle(pi.hThread);
}
