// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/df.h"

#include <array>
#include <iostream>
#include <string>

#include "common/wtools.h"
#include "tools/_raii.h"
#include "tools/_win.h"
#include "tools/_xlog.h"

namespace cma::provider {

namespace df {
std::pair<std::string, std::string> GetNamesByVolumeId(
    std::string_view volume_id) {
    constexpr DWORD file_system_size = 128;
    constexpr DWORD volume_name_size = 512;
    std::array<char, file_system_size> filesystem_name = {};  // zero init
    std::array<char, volume_name_size> volume_name = {};      // zero init

    DWORD flags = 0;
    if (::GetVolumeInformationA(volume_id.data(), volume_name.data(),
                                volume_name_size, nullptr, nullptr, &flags,
                                filesystem_name.data(),
                                file_system_size) == FALSE) {
        filesystem_name[0] =
            '\0';  // May be necessary if partial information returned
        XLOG::d("Information for volume '{}' is not available [{}]", volume_id,
                ::GetLastError());
    }

    return {filesystem_name.data(), volume_name.data()};
}

std::pair<uint64_t, uint64_t> GetSpacesByVolumeId(std::string_view volume_id) {
    ULARGE_INTEGER avail{.QuadPart = 0};
    ULARGE_INTEGER total{.QuadPart = 0};
    ULARGE_INTEGER free{.QuadPart = 0};
    int ret = ::GetDiskFreeSpaceExA(volume_id.data(), &avail, &total, &free);
    if (ret == FALSE) {
        XLOG::d("GetDiskFreeSpaceExA is failed with error [{}]",
                ::GetLastError());
        return {0, 0};
    }
    return {avail.QuadPart, total.QuadPart};
}

uint64_t CalcUsage(uint64_t avail, uint64_t total) {
    if (avail > total) return 0;
    if (total == 0) return 0;

    return 100 - (100 * avail) / total;
}

std::string ProduceFileSystemOutput(std::string_view volume_id) {
    auto [fs_name, volume_name] = df::GetNamesByVolumeId(volume_id);
    auto [avail, total] = df::GetSpacesByVolumeId(volume_id);

    auto usage = CalcUsage(avail, total);

    if (volume_name.empty())  // have a volume name
        volume_name = volume_id;
    else
        std::replace(volume_name.begin(), volume_name.end(), ' ', '_');

    return fmt::format("{}\t{}\t{}\t{}\t{}\t{}%\t{}\n",  //
                       volume_name,                      //
                       fs_name,                          //
                       total / 1024,                     //
                       (total - avail) / 1024,           //
                       avail / 1024,                     //
                       usage,                            //
                       volume_id);
}

std::vector<std::string> GetMountPointVector(std::string_view volume_id) {
    constexpr int sz = 2048;
    auto storage = std::make_unique<char[]>(sz);

    std::vector<std::string> result;

    XLOG::t("Volume is '{}'", volume_id);
    auto* handle =
        ::FindFirstVolumeMountPointA(volume_id.data(), storage.get(), sz);

    if (wtools::IsBadHandle(handle)) return {};
    ON_OUT_OF_SCOPE(FindVolumeMountPointClose(handle));

    std::string vol(volume_id);
    while (true) {
        result.emplace_back(vol + storage.get());

        auto success = ::FindNextVolumeMountPointA(handle, storage.get(), sz);
        if (success == FALSE) {
            auto error = ::GetLastError();
            if (error != ERROR_NO_MORE_FILES)
                XLOG::l("Error  [{}] looking for volume '{}'", error,
                        volume_id);
            break;
        }
        XLOG::t("Next mount point '{}'", storage.get());
    }

    return result;
}

std::string ProduceMountPointsOutput(const std::string& volume_id) {
    constexpr int sz = 2048;
    auto storage = std::make_unique<char[]>(sz);

    XLOG::t("Volume is '{}'", volume_id);
    auto* handle =
        ::FindFirstVolumeMountPointA(volume_id.c_str(), storage.get(), sz);

    if (wtools::IsBadHandle(handle)) {
        XLOG::d("Failed FindFirstVolumeMountPointA, error is [{}]",
                ::GetLastError());
        return {};
    }
    ON_OUT_OF_SCOPE(::FindVolumeMountPointClose(handle));

    std::string out;

    const auto combined_path = volume_id + storage.get();
    while (true) {
        out += ProduceFileSystemOutput(combined_path);
        out += ProduceMountPointsOutput(combined_path);

        auto success = ::FindNextVolumeMountPointA(handle, storage.get(), sz);
        if (FALSE == success) {
            auto error = ::GetLastError();
            if (error != ERROR_NO_MORE_FILES)
                XLOG::l("Error  [{}] looking for volume '{}'", error,
                        volume_id);
            break;
        }
        XLOG::t("Next mount point '{}'", storage.get());
    }

    return out;
}

std::vector<std::string> GetDriveVector() {
    constexpr int sz = 2048;
    auto drive_string_buffer = std::make_unique<char[]>(sz);
    auto len = ::GetLogicalDriveStringsA(sz, drive_string_buffer.get());

    auto* end = drive_string_buffer.get() + len;
    auto* drive = drive_string_buffer.get();

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

std::string Df::makeBody() {
    std::string out;
    auto drives = df::GetDriveVector();
    XLOG::t("Processing of [{}] drives", drives.size());

    int count = 0;
    for (auto& drive : drives) {
        auto drive_type = ::GetDriveTypeA(drive.c_str());

        if (drive_type == DRIVE_FIXED)  // means local hard disks
        {
            out += df::ProduceFileSystemOutput(drive);
            out += df::ProduceMountPointsOutput(drive);
            count++;
        } else
            XLOG::t("Drive '{}' is skipped due to type [{}]", drive,
                    drive_type);
    }
    XLOG::d.i("Processed [{}] drives", count);

    return out;
}

};  // namespace cma::provider
