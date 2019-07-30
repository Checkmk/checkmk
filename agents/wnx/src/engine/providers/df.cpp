
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/df.h"

#include <iostream>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

static auto GetNamesByVolumeId(const std::string &VolumeId) {
    using namespace std;
    char filesystem_name[128] = {0};
    char volume_name[512] = {0};
    DWORD flags = 0;
    if (!::GetVolumeInformationA(VolumeId.c_str(), volume_name,
                                 sizeof(volume_name), 0, 0, &flags,
                                 filesystem_name, sizeof(filesystem_name))) {
        filesystem_name[0] =
            '\0';  // May be necessary if partial information returned
    }

    return make_tuple(string(filesystem_name), string(volume_name));
}

static auto GetSpacesByVolumeId(const std::string &VolumeId) {
    using namespace std;
    ULARGE_INTEGER avail, total, free;
    avail.QuadPart = 0;
    total.QuadPart = 0;
    free.QuadPart = 0;
    int ret = ::GetDiskFreeSpaceExA(VolumeId.c_str(), &avail, &total, &free);
    if (ret == 0) {
        avail.QuadPart = 0;
        total.QuadPart = 0;
    }
    return make_tuple(avail.QuadPart, total.QuadPart);
}

// wrapper for win32
static std::string GetFileSystem(const std::string VolumeId) {
    auto [fs_name, volume_name] = GetNamesByVolumeId(VolumeId);
    auto [avail, total] = GetSpacesByVolumeId(VolumeId);

    auto usage = total > 0 ? 100 - (100 * avail / total) : 0;

    if (volume_name.empty())  // have a volume name
        volume_name = VolumeId;
    else
        std::replace(volume_name.begin(), volume_name.end(), ' ', '_');

    return fmt::format("{}\t{}\t{}\t{}\t{}\t{}%\t{}\n",  //
                       volume_name,                      //
                       fs_name,                          //
                       total / 1024,                     //
                       (total - avail) / 1024,           //
                       avail / 1024,                     //
                       usage,                            //
                       VolumeId);
}

std::string GetMountPoints(const std::string &VolumeId) {
    char mountpoint[512] = "";
    auto handle = ::FindFirstVolumeMountPointA(VolumeId.c_str(), mountpoint,
                                               sizeof(mountpoint));

    if (!handle || handle == INVALID_HANDLE_VALUE) return {};
    ON_OUT_OF_SCOPE(FindVolumeMountPointClose(handle));

    std::string out;
    while (true) {
        const std::string combined_path = VolumeId + mountpoint;
        out += GetFileSystem(combined_path);
        out += GetMountPoints(combined_path);

        if (::FindNextVolumeMountPointA(handle, mountpoint, sizeof(mountpoint)))
            break;
    }
    return out;
}

std::string Df::makeBody() {
    XLOG::t(XLOG_FUNC + " entering");

    char buffer[4096];
    DWORD len = ::GetLogicalDriveStringsA(sizeof(buffer), buffer);

    char *end = buffer + len;
    char *drive = buffer;
    std::string out;
    while (drive < end) {
        UINT drvType = ::GetDriveTypeA(drive);
        if (drvType == DRIVE_FIXED)  // only process local harddisks
        {
            out += GetFileSystem(drive);
            out += GetMountPoints(drive);
        }
        drive += strlen(drive) + 1;
    }

    return out;
}

}  // namespace provider
};  // namespace cma
