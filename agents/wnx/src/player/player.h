// HEADER ONLY(mostly) Player Engine

#pragma once
#include <filesystem>
#include <iostream>
#include <optional>
#include <string>

#include "cma_core.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "logger.h"
#include "tools/_misc.h"
#include "tools/_xlog.h"

namespace cma::player {
constexpr int kMaxPluginsToExec = 32;
inline bool SendDataThroughCarrier() {}

// unit to execute one or more executables
// async
class TheBox {
public:
    TheBox() {}
    TheBox(const TheBox&) = delete;
    TheBox& operator=(const TheBox&) = delete;

    // #TODO implement movers!
    TheBox(const TheBox&&) = delete;
    TheBox& operator=(const TheBox&&) = delete;

    ~TheBox() { clean(); }

    size_t start(std::wstring Id, const std::vector<std::wstring> ExecArray) {
        int count = 0;
        std::lock_guard lk(lock_);
        if (processes_.size() != 0) return 0;
        id_ = Id;

        // send exec array entries to internal
        try {
            processExecArray(ExecArray);
            // now exec all
            for (auto& exec : exec_array_) {
                auto ar = new wtools::AppRunner;
                auto started = ar->goExecAsJob(exec);
                if (started)
                    processes_.push_back(ar);
                else
                    delete ar;  // start failed
            }
        } catch (const std::exception& e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        return processes_.size();
    }

    size_t start(std::wstring Id, const std::filesystem::path ExeFile) {
        int count = 0;
        std::lock_guard lk(lock_);
        if (processes_.size() != 0) return 0;
        id_ = Id;

        // send exec array entries to internal
        try {
            std::vector<std::wstring> exec_array;
            exec_array.push_back(ExeFile.wstring());
            processExecArray(exec_array);
            // now exec all
            for (auto& exec : exec_array_) {
                auto ar = new wtools::AppRunner;
                auto started = ar->goExecAsJob(exec);
                if (started)
                    processes_.push_back(ar);
                else
                    delete ar;  // start failed
            }
        } catch (const std::exception& e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        return processes_.size();
    }

    // make array of read handles
    std::vector<HANDLE> gatherReadHandles() {
        std::vector<HANDLE> handles;
        std::unique_lock lk(lock_);
        for (auto& app : processes_) {
            auto h = app->getStdioRead();
            if (h) handles.push_back(h);
        }
        lk.unlock();
        return handles;
    }

    std::vector<uint32_t> gatherProcessId() {
        std::vector<uint32_t> proc_id;
        std::unique_lock lk(lock_);
        for (auto& app : processes_) {
            auto pid = app->processId();
            if (pid) proc_id.push_back(pid);
        }
        lk.unlock();
        return proc_id;
    }

    bool appendResult(HANDLE Handle, std::vector<char>& Buf) {
        using namespace std;
        if (Buf.size() == 0) return true;

        lock_guard lk(lock_);
        for (auto& app : processes_) {
            auto h = app->getStdioRead();
            if (h && h == Handle) {
                cma::tools::AddVector(app->getData(), Buf);
                return true;
            }
        }
        return false;
    }

    bool storeExitCode(uint32_t Pid, uint32_t Code) {
        using namespace std;
        lock_guard lk(lock_);
        for (auto& app : processes_) {
            if (app->trySetExitCode(Pid, Code)) return true;
        }
        return false;
    }

    // add content of file to the Buf
    template <typename T>
    bool appendFileContent(T& Buf, HANDLE h, size_t Count) const noexcept {
        // check what we have already inside
        auto buf_size = Buf.size();
        try {
            Buf.resize(buf_size + Count);
        } catch (const std::exception& e) {
            xlog::l(XLOG_FLINE + " exception: %s", e.what());
            return false;
        }

        // add new data
        auto read_buffer = Buf.data() + buf_size;
        DWORD read_in_fact = 0;
        auto count = static_cast<DWORD>(Count);
        auto result = ::ReadFile(h, read_buffer, count, &read_in_fact, nullptr);
        if (!result) false;

        if (buf_size + read_in_fact != Buf.size()) {
            Buf.resize(buf_size + read_in_fact);
        }

        return true;
    }

    // With kGrane interval tries to check running processes
    // returns true if all processes ended or disappeared
    bool waitForAllProcesses(std::chrono::milliseconds Timeout,
                             bool KillWhatLeft) {
        using namespace std;
        using namespace std::chrono;
        ON_OUT_OF_SCOPE(readWhatLeft());

        constexpr milliseconds kGrane = 500ms;
        auto waiting_processes = gatherProcessId();
        vector<HANDLE> read_handles = gatherReadHandles();
        for (;;) {
            waiting_processes = updateProcessExitCode(waiting_processes);
            {
                for (auto h : read_handles) {
                    auto buf = readFromHandle<vector<char>>(h);
                    if (buf.size()) appendResult(h, buf);
                }
            }

            if (waiting_processes.size() == 0) return true;

            if (Timeout >= kGrane) {
                // #TODO replace with conditional variable
                std::this_thread::sleep_until(steady_clock::now() + kGrane);
                Timeout -= kGrane;
                continue;
            }

            if (KillWhatLeft) {
                for (auto pid : waiting_processes) {
                    wtools::KillProcess(pid, -1);
                    XLOG::d("Process [{}] killed",
                            pid);  // abnormal situation
                }
            }

            return false;
        }

        // never here
    }

    void clean() {
        exec_array_.resize(0);
        std::unique_lock lk(lock_);
        auto processes = std::move(processes_);
        lk.unlock();

        for (auto& app : processes) {
            delete app;
        }
    }

    void processResults(
        std::function<void(const std::wstring CmdLine, uint32_t Pid,
                           uint32_t Code, const std::vector<char>& Data)>
            Func) {
        std::unique_lock lk(lock_);
        for (auto p : processes_) {
            Func(p->getCmdLine(), p->processId(), p->exitCode(), p->getData());
        }
    }

private:
    // called AFTER process finished!
    void readWhatLeft() {
        using namespace std;
        vector<HANDLE> read_handles = gatherReadHandles();
        for (auto h : read_handles) {
            auto buf = readFromHandle<vector<char>>(h);
            if (buf.size()) appendResult(h, buf);
        }
    }

    int processExecArray(const std::vector<std::wstring>& ExecArray) {
        int count = 0;
        for (auto& exec_entry : ExecArray) {
            using namespace std::filesystem;
            path p = exec_entry;
            if (!exists(p)) continue;

            if (is_directory(p)) {
                // this is bad idea
                for (auto& dir_entry : directory_iterator(p)) {
                    auto p_entry = dir_entry.path();

                    if (tryAddToExecArray(p_entry)) count++;
                }
            } else {
                if (tryAddToExecArray(p)) count++;
            }
        }
        return count;
    }

    template <typename T>
    T readFromHandle(HANDLE Handle) {
        T buf;
        for (;;) {
            auto read_count = wtools::DataCountOnHandle(Handle);

            // now reading to the end
            if (read_count == 0) break;                              // no data
            if (!appendFileContent(buf, Handle, read_count)) break;  // io fail
        }
        return buf;
    }

    // check all processes in list for exit
    // updates object
    // returns list of active processes
    std::vector<uint32_t> updateProcessExitCode(
        const std::vector<uint32_t>& Processes) {
        using namespace std;
        vector<uint32_t> waiting_processes;
        for (auto pid : Processes) {
            auto h = OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,  // not supported on XP
                FALSE, pid);
            if (h) {
                ON_OUT_OF_SCOPE(CloseHandle(h));
                DWORD exit_code = 0;
                auto success = GetExitCodeProcess(h, &exit_code);
                if (success) {
                    if (exit_code == STILL_ACTIVE) {
#if (0)
                        // disabled due to high noise
                        XLOG::t("Process [{}] is active", pid);
#endif  // endif
                        waiting_processes.push_back(pid);
                    } else {
                        // store exit code
                        XLOG::t("Process [{}] has exit code [{}]", pid,
                                exit_code);
                        storeExitCode(pid, exit_code);
                    }
                } else {
                    XLOG::l(XLOG_FLINE + " Ups error {}", GetLastError());
                }
            } else {
                storeExitCode(pid, 0);  // process died
                XLOG::d("Process {} is failed to open, err = {}", pid,
                        GetLastError());
            }
        }
        return waiting_processes;
    }

    bool isExecValid(const std::filesystem::path& FileExec) const {
        if (!IsValidFile(FileExec)) return false;  // sanity

        if (exec_array_.size() > kMaxPluginsToExec) return false;  // !

        auto execute_string = ConstructCommandToExec(FileExec);
        if (execute_string.empty()) {
            XLOG::l("Can\'t create exe string for the {}", FileExec.u8string());
            return false;
        }

        return true;
    }

    bool isExecIn(const std::filesystem::path& FileExec) {
        using namespace std::filesystem;
        using namespace std;

        // now check for duplicates:
        auto stringToSearch = ConstructCommandToExec(FileExec);
        auto found = find_if(
            exec_array_.begin(), exec_array_.end(),
            [stringToSearch](const wstring FromExec) {
                if (FromExec.size() != stringToSearch.size()) return false;
                for (size_t i = 0; i < FromExec.size(); ++i)
                    if (::tolower(FromExec[i]) != ::tolower(stringToSearch[i]))
                        return false;
                return true;
            });

        if (found == exec_array_.end()) return true;  // exec is absent
        return false;
    }

private:
    bool tryAddToExecArray(const std::filesystem::path& FileExec) {
        using namespace std::filesystem;
        using namespace std;

        if (!isExecValid(FileExec)) return false;
        if (!isExecIn(FileExec)) return false;

        auto execute_string = ConstructCommandToExec(FileExec);

        exec_array_.emplace_back(execute_string);
        return true;
    }

    std::wstring cmd_;
    std::wstring id_;
    std::vector<std::wstring> exec_array_;

    std::mutex lock_;
    std::vector<wtools::AppRunner*>
        processes_;  // #TODO ? replace with unique_ptr

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class PlayerTest;
    FRIEND_TEST(PlayerTest, All);
    FRIEND_TEST(PlayerTest, Extensions);
    FRIEND_TEST(PlayerTest, RealLifeInventory_Long);
    FRIEND_TEST(v, StartStop);
#endif
};

};  // namespace cma::player
