// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "SectionDF.h"
#include "../stringutil.h"
#include <iomanip>


void char_replace(char what, char into, char *in) {
    while (*in) {
        if (*in == what) *in = into;
        in++;
    }
}


SectionDF::SectionDF()
    : Section("df", "df")
{
    withSeparator('\t');
}

void SectionDF::output_filesystem(std::ostream &out, char *volid) {
    static const int KiloByte = 1024;

    TCHAR fsname[128];
    TCHAR volume[512];
    DWORD dwSysFlags = 0;
    if (!GetVolumeInformation(volid, volume, sizeof(volume), 0, 0, &dwSysFlags,
                              fsname, sizeof(fsname)))
        fsname[0] = 0;

    ULARGE_INTEGER free_avail, total, free;
    free_avail.QuadPart = 0;
    total.QuadPart = 0;
    free.QuadPart = 0;
    int returnvalue = GetDiskFreeSpaceEx(volid, &free_avail, &total, &free);
    if (returnvalue > 0) {
        double perc_used = 0;
        if (total.QuadPart > 0)
            perc_used = 100 - (100 * free_avail.QuadPart / total.QuadPart);

        if (volume[0])  // have a volume name
            char_replace(' ', '_', volume);
        else
            strncpy(volume, volid, sizeof(volume));

        out << volume << "\t"
            << fsname << "\t"
            << (total.QuadPart / KiloByte) << "\t"
            << (total.QuadPart - free_avail.QuadPart) / KiloByte << "\t"
            << (free_avail.QuadPart / KiloByte) << "\t"
            << std::fixed << std::setprecision(0) << perc_used << "%\t"
            << volid
            << "\n";
    }
}

void SectionDF::output_mountpoints(std::ostream &out, char *volid) {
    char mountpoint[512];
    HANDLE hPt =
        FindFirstVolumeMountPoint(volid, mountpoint, sizeof(mountpoint));
    if (hPt != INVALID_HANDLE_VALUE) {
        while (true) {
            TCHAR combined_path[1024];
            snprintf(combined_path, sizeof(combined_path), "%s%s", volid,
                     mountpoint);
            output_filesystem(out, combined_path);
            if (!FindNextVolumeMountPoint(hPt, mountpoint, sizeof(mountpoint)))
                break;
        }
        FindVolumeMountPointClose(hPt);
    }
}

bool SectionDF::produceOutputInner(std::ostream &out, const Environment &env) {
    TCHAR buffer[4096];
    DWORD len = GetLogicalDriveStrings(sizeof(buffer), buffer);

    TCHAR *end = buffer + len;
    TCHAR *drive = buffer;
    while (drive < end) {
        UINT drvType = GetDriveType(drive);
        if (drvType == DRIVE_FIXED)  // only process local harddisks
        {
            output_filesystem(out, drive);
            output_mountpoints(out, drive);
        }
        drive += strlen(drive) + 1;
    }

    // Output volumes, that have no drive letter. The following code
    // works, but then we have no information about the drive letters.
    // And if we run both, then volumes are printed twice. So currently
    // we output only fixed drives and mount points below those fixed
    // drives.

    // HANDLE hVolume;
    // char volid[512];
    // hVolume = FindFirstVolume(volid, sizeof(volid));
    // if (hVolume != INVALID_HANDLE_VALUE) {
    //     df_output_filesystem(out, volid);
    //     while (true) {
    //         // df_output_mountpoints(out, volid);
    //         if (!FindNextVolume(hVolume, volid, sizeof(volid)))
    //             break;
    //     }
    //     FindVolumeClose(hVolume);
    // }

    return true;
}

