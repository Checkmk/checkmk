
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/df.h"

#include <iostream>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

namespace df {
std::pair<std::string, std::string> GetNamesByVolumeId(
    std::string_view volume_id) {
    char filesystem_name[128] = {0};
    char volume_name[512] = {0};

    DWORD flags = 0;
    if (!::GetVolumeInformationA(volume_id.data(), volume_name,
                                 sizeof(volume_name), 0, 0, &flags,
                                 filesystem_name, sizeof(filesystem_name))) {
        filesystem_name[0] =
            '\0';  // May be necessary if partial information returned
        XLOG::d("df: Information for volume '{}' is not available [{}]",
                volume_id, ::GetLastError());
    }

    return {filesystem_name, volume_name};
}

std::pair<uint64_t, uint64_t> GetSpacesByVolumeId(std::string_view volume_id) {
    ULARGE_INTEGER avail, total, free;
    avail.QuadPart = 0;
    total.QuadPart = 0;
    free.QuadPart = 0;
    int ret = ::GetDiskFreeSpaceExA(volume_id.data(), &avail, &total, &free);
    if (ret == 0) {
        avail.QuadPart = 0;
        total.QuadPart = 0;
    }
    return {avail.QuadPart, total.QuadPart};
}

uint64_t CalcUsage(uint64_t avail, uint64_t total) {
    if (avail > total) return 0;
    if (total == 0) return 0;

    return 100 - (100 * avail) / total;
}

// wrapper for win32
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

// #TODO integrate in solution
std::vector<std::string> GetMountPointVector(std::string_view volume_id) {
    constexpr int sz = 2048;
    auto storage = std::make_unique<char[]>(sz);

    std::vector<std::string> result;

    XLOG::t("df: Volume is '{}'", volume_id);
    auto handle =
        ::FindFirstVolumeMountPointA(volume_id.data(), storage.get(), sz);

    if (!handle || handle == INVALID_HANDLE_VALUE) return {};
    ON_OUT_OF_SCOPE(FindVolumeMountPointClose(handle));

    std::string vol(volume_id);
    while (true) {
        result.emplace_back(vol + storage.get());

        auto success = ::FindNextVolumeMountPointA(handle, storage.get(), sz);
        if (!success) {
            auto error = ::GetLastError();
            if (error != ERROR_NO_MORE_FILES)
                XLOG::l("df: Error  [{}] looking for volume '{}'", error,
                        volume_id);
            break;
        }
        XLOG::t("df: Next mount point '{}'", storage.get());
    }

    return result;
}

std::string ProduceMountPointsOutput(const std::string& VolumeId) {
    constexpr int sz = 2048;
    auto storage = std::make_unique<char[]>(sz);

    XLOG::t("df: Volume is '{}'", VolumeId);
    auto handle =
        ::FindFirstVolumeMountPointA(VolumeId.c_str(), storage.get(), sz);

    if (!handle || handle == INVALID_HANDLE_VALUE) return {};
    ON_OUT_OF_SCOPE(FindVolumeMountPointClose(handle));

    std::string out;

    while (true) {
        const std::string combined_path = VolumeId + storage.get();
        out += ProduceFileSystemOutput(combined_path);
        out += ProduceMountPointsOutput(combined_path);

        auto success = ::FindNextVolumeMountPointA(handle, storage.get(), sz);
        if (!success) {
            auto error = ::GetLastError();
            if (error != ERROR_NO_MORE_FILES)
                XLOG::l("df: Error  [{}] looking for volume '{}'", error,
                        VolumeId);
            break;
        }
        XLOG::t("df: Next mount point '{}'", storage.get());
    }

    return out;
}

std::vector<std::string> GetDriveVector() noexcept {
    std::vector<std::string> drives;
    constexpr int sz = 2048;
    auto buffer = std::make_unique<char[]>(sz);
    auto len = ::GetLogicalDriveStringsA(sz, buffer.get());

    auto end = buffer.get() + len;
    auto drive = buffer.get();

    while (drive < end) {
        auto drvType = ::GetDriveTypeA(drive);

        if (drvType != DRIVE_UNKNOWN) drives.emplace_back(drive);

        drive += strlen(drive) + 1;
    }

    return drives;
}
}  // namespace df

std::string Df::makeBody() {
    XLOG::t(XLOG_FUNC + " entering");

    std::string out;
    auto drives = df::GetDriveVector();
    XLOG::t("Processing of [{}] drives", drives.size());

    int count = 0;
    for (auto& drive : drives) {
        auto drive_type = ::GetDriveTypeA(drive.c_str());

        // #FEATURE 'removable support' future
        if (drive_type == DRIVE_FIXED)  // only process local hard disks
        {
            out += df::ProduceFileSystemOutput(drive);
            out += df::ProduceMountPointsOutput(drive);
            count++;
        } else
            XLOG::t("df: Drive '{}' is skipped due to type [{}]", drive,
                    drive_type);
    }
    XLOG::d.t("df: Processed [{}] drives", count);

    return out;
}

}  // namespace provider
};  // namespace cma
