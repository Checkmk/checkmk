// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/df.h"

#include <array>
#include <iostream>
#include <string>

#include "common/wtools.h"
#include "tools/_win.h"

namespace rs = std::ranges;

namespace cma::provider {

namespace df {
std::pair<std::string, std::string> GetNamesByVolumeId(
    std::string_view volume_id) {
    constexpr DWORD file_system_size = 128;
    constexpr DWORD volume_name_size = 512;
    std::array<char, file_system_size> filesystem_name = {};
    std::array<char, volume_name_size> volume_name = {};

    DWORD flags = 0;
    if (::GetVolumeInformationA(volume_id.data(), volume_name.data(),
                                volume_name_size, nullptr, nullptr, &flags,
                                filesystem_name.data(),
                                file_system_size) == FALSE) {
        filesystem_name[0] = '\0';  // if partial information returned
        XLOG::d("Information for volume '{}' is not available [{}]", volume_id,
                ::GetLastError());
    }

    return {filesystem_name.data(), volume_name.data()};
}

std::pair<uint64_t, uint64_t> GetSpacesByVolumeId(std::string_view volume_id) {
    ULARGE_INTEGER avail{.QuadPart = 0};
    ULARGE_INTEGER total{.QuadPart = 0};
    ULARGE_INTEGER free{.QuadPart = 0};
    if (::GetDiskFreeSpaceExA(volume_id.data(), &avail, &total, &free) ==
        FALSE) {
        XLOG::d("GetDiskFreeSpaceExA for volume '{}' is failed with error [{}]",
                volume_id, ::GetLastError());
        return {0, 0};
    }
    return {avail.QuadPart, total.QuadPart};
}

uint64_t CalcUsage(uint64_t avail, uint64_t total) noexcept {
    if (avail > total || total == 0) {
        return 0;
    }

    return 100 - 100 * avail / total;
}

std::string ProduceFileSystemOutput(std::string_view volume_id) {
    auto [fs_name, volume_name] = df::GetNamesByVolumeId(volume_id);
    auto [avail, total] = df::GetSpacesByVolumeId(volume_id);

    if (volume_name.empty())
        volume_name = volume_id;
    else
        rs::replace(volume_name, ' ', '_');

    return fmt::format("{}\t{}\t{}\t{}\t{}\t{}%\t{}\n",  //
                       volume_name,                      //
                       fs_name,                          //
                       total / 1024,                     //
                       (total - avail) / 1024,           //
                       avail / 1024,                     //
                       CalcUsage(avail, total),          //
                       volume_id);
}

class VolumeMountData {
public:
    VolumeMountData(const VolumeMountData &) = delete;
    VolumeMountData &operator=(const VolumeMountData &) = delete;
    VolumeMountData(const VolumeMountData &&) = delete;
    VolumeMountData &operator=(VolumeMountData &&) = delete;

    explicit VolumeMountData(std::string_view volume_id)
        : storage_{std::make_unique<char[]>(sz_)}
        , volume_id_{volume_id}
        , handle_{::FindFirstVolumeMountPointA(volume_id.data(), storage_.get(),
                                               sz_)} {
        XLOG::t("Volume is '{}'", volume_id_);
    }

    ~VolumeMountData() {
        if (!wtools::IsBadHandle(handle_)) {
            ::FindVolumeMountPointClose(handle_);
        }
    }

    bool next() {
        auto ret =
            ::FindNextVolumeMountPointA(handle_, storage_.get(), sz_) == TRUE;

        if (ret == FALSE) {
            auto error = ::GetLastError();
            if (error != ERROR_NO_MORE_FILES)
                XLOG::l("Error [{}] looking for volume '{}'", error,
                        volume_id_);
        }

        return ret;
    }

    [[nodiscard]] bool exists() const { return !wtools::IsBadHandle(handle_); }
    [[nodiscard]] std::string result() const { return storage_.get(); }

private:
    constexpr static int sz_{2048};
    std::unique_ptr<char[]> storage_;
    std::string volume_id_;
    HANDLE handle_{nullptr};
};

std::vector<std::string> GetMountPointVector(std::string_view volume_id) {
    VolumeMountData vmd(volume_id);
    if (!vmd.exists()) return {};

    std::vector<std::string> result;
    std::string vol(volume_id);
    while (true) {
        result.emplace_back(vol + vmd.result());

        if (!vmd.next()) {
            break;
        }
        XLOG::t("Next mount point '{}'", vmd.result());
    }

    return result;
}

std::string ProduceMountPointsOutput(std::string_view volume_id) {
    VolumeMountData vmd(volume_id);

    if (!vmd.exists()) {
        if (::GetLastError() != ERROR_NO_MORE_FILES) {
            XLOG::d(
                "Failed FindFirstVolumeMountPointA at volume '{}', error is [{}]",
                volume_id, ::GetLastError());
        }
        return {};
    }

    std::string out;

    while (true) {
        auto combined_path = std::string{volume_id} + vmd.result();
        out += ProduceFileSystemOutput(combined_path);
        out += ProduceMountPointsOutput(combined_path);  // recursion! here

        if (!vmd.next()) {
            break;
        }
        XLOG::t("Next mount point '{}'", vmd.result());
    }

    return out;
}

std::vector<std::string> GetDriveVector() {
    constexpr int sz = 2048;
    auto drive_string_buffer = std::make_unique<char[]>(sz);
    auto len = ::GetLogicalDriveStringsA(sz, drive_string_buffer.get());

    auto *end = drive_string_buffer.get() + len;
    auto *drive = drive_string_buffer.get();

    std::vector<std::string> drives;
    while (drive < end) {
        if (::GetDriveTypeA(drive) != DRIVE_UNKNOWN) {
            drives.emplace_back(drive);
        }
        drive += strlen(drive) + 1;
    }

    return drives;
}
}  // namespace df

namespace {

bool IsFixedDrive(std::string_view volume_id) {
    return ::GetDriveTypeA(volume_id.data()) == DRIVE_FIXED;
}

std::string ProduceFormattedInfoForFixedDrive(std::string_view volume_id) {
    return IsFixedDrive(volume_id) ? df::ProduceFileSystemOutput(volume_id) +
                                         df::ProduceMountPointsOutput(volume_id)
                                   : std::string{};
}

std::pair<std::string, int> ProduceFormattedInfoForFixedDrives(
    const std::vector<std::string> &volumes) {
    std::string out;
    int count = 0;
    for (const auto &v : volumes) {
        const auto fixed_drive_info = ProduceFormattedInfoForFixedDrive(v);
        if (fixed_drive_info.empty()) {
            XLOG::t("Volume '{}' is skipped", v);
            continue;
        }
        count++;
        out += fixed_drive_info;
    }
    return {out, count};
}

}  // namespace

std::string Df::makeBody() {
    const auto drives = df::GetDriveVector();
    XLOG::t("Processing of [{}] drives", drives.size());

    const auto [output, count] = ProduceFormattedInfoForFixedDrives(drives);
    XLOG::d.i("Processed [{}] fixed drives of total [{}]", count,
              drives.size());

    return output;
}

}  // namespace cma::provider
