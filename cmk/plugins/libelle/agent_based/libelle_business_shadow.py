#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS

#   .--Example output from agent-------------------------------------------.
# <<<libelle_business_shadow:sep(58)>>>
#   DBShadow Oracle                           Libelle AG
#   trd : Shared Memory
#   Release: 5.7.6.0.053 (31003)
#
#   Process-Id           : 7929872
#   Start-Time           : 12.05.2014 16:55
#   Shm-Id               : 2097154
#   Sem-Id               : 23068672
#   Number DB            : 2
#   Company              : khkirchheim
#   DB Size              : 999
#   Business             : 2
#   Long-Distance        : 0
#   Raw-Device           : 0
#   Flat-Files           : 0
#   Trace                : OFF
#   Host                 : kkn-dbnode1-2351
#   System               : aix.61
#   Status               : RUN
#   Authentication Type  : none
#
#   -------------- TRD-Parameter --------------
#   TRD_ARCHDIR_REPEAT            : 30
#   TRD_ARCHIVER_TYPE             : turbo
#   TRD_AUDIT_TRAIL               : FALSE
#   TRD_CHECK_RELEASE             : TRUE
#   TRD_COPYWAIT                  : 0/0
#   TRD_COPY_DELETE_BACKUPFILES   : NONE
#   TRD_DISKSPACE                 : 70/90
#   TRD_FFARCHIVEFILE_SIZE        : 10
#   TRD_FFBACKUPBLOCK_SIZE        : 10
#   TRD_FFBACKUPFILE_SIZE         : 100
#   TRD_FFCHECK_PERM              : TRUE
#   TRD_FFLOGFORMAT               : ff__.ars
#   TRD_FILE_ACCESS               : FILE_POINTER
#   TRD_FILE_BUFFER_SIZE          : 1
#   TRD_FI_OWNER_ERRORLEVEL       : warning
#   TRD_FI_PERM_ERRORLEVEL        : warning
#   TRD_FI_TIME_ERRORLEVEL        : warning
#   TRD_HOME                      : /opt/libelle
#   TRD_HOME_SIZE_REQUIRED        : 1000
#   TRD_HOSTNAME                  : kkn-dbnode1-2351
#   TRD_LANGUAGE                  : english
#   TRD_MAIL_LOCALINTERFACE       :
#   TRD_MAX_CONNECTIONS           : 100
#   TRD_MAX_FF_ENTRIES            : 200
#   TRD_MAX_MAPPINGS              : 200
#   TRD_MAX_USER_MAPPINGS         : 200
#   TRD_PARALLEL_TRANS_PORTS      :
#   TRD_PORT                      : 7200
#   TRD_POWERUP                   : 0
#   TRD_RECOVERTIMEOUT            : 1500
#   TRD_ROOT_ALLOW                : FALSE
#   TRD_SAVE_DELETE               : 7
#   TRD_SAVE_SIZE                 : 5
#   TRD_SIGCLD_RESET              : FALSE
#   TRD_SOCKETLEN                 : 32
#   TRD_SOCKETTIMEOUT             : 120
#   TRD_SOCKET_BLOCKING           : FALSE
#   TRD_SPFILE_PATH               : DEFAULT
#   TRD_TIMEOUT                   : 60
#   TRD_TRACELEVEL                : 30
#   TRD_UI_NUM                    : 20
#   TRD_USE_ACCOUNT_TYPE          : local
#
#   -------------- Process List --------------
#   Pid : 7929872   -1                               Timestamp : 22.05.2014 17:36:38   Type : main
#   Pid : 7929872   -258                             Timestamp : 22.05.2014 17:36:38   Type : listen
#   Pid : 2556268   -1                               Timestamp : 22.05.2014 17:36:37   Type : recover KHVN1
#
#   ============== Configuration KHVN1 ===============
#
#   -------------- Parameter -----------------
#   APPLICATION_SYSTEM             =
#   ARCHIVE_ALTERNATE_PATH         = /u02/oradata/khvn/archive_stby
#   ARCHIVE_CHECK_DB               = 1
#   ARCHIVE_COLD                   = FALSE
#   ARCHIVE_DELETE                 = TRUE
#   ARCHIVE_MAX_SWITCH             = 20
#   ARCHIVE_NUM                    = 131511
#   ARCHIVE_PATH                   = /u02/oradata/khvn/archive
#   ARCHIVE_PIPE                   = TRUE
#   ARCHIVE_SHIP_LOGFILES          = TRUE
#   ARCHIVE_STATUS                 = RUN
#   CHECK_DISKSPACE                = TRUE
#   COMPRESSED_COPY                = TRUE
#   COPY_BACK                      = FALSE
#   COPY_BACKUP_DIRECTORY          =
#   COPY_CHECK_MIRROR              = TRUE
#   COPY_COLD                      = FALSE
#   COPY_CONTINUE                  = FALSE
#   COPY_FROM_COPY                 =
#   COPY_START_ARCHIVER            = TRUE
#   COPY_START_RECOVER             = TRUE
#   COPY_STATUS                    = STOP
#   CREATE_DIRECTORY               = FALSE
#   CREATE_FULL_DIRECTORY          = TRUE
#   CURRENT_FUNCTION               = recover
#   CURRENT_STATUS                 = 20140522 17:36:17;normal;archiver:131511;recover:131492;
#   CUSTOM1                        =
#   CUSTOM2                        =
#   DBS_PATH                       =
#   DB_USER                        =
#   DEFINED_SWITCH                 = FALSE
#   DESCRIPTION                    = KHVN1
#   EMERGENCY_AUTOMATIC            = FALSE
#   EMERGENCY_SID                  =
#   EMERGENCY_WAIT_TIME            = 0
#   EXTERNAL_BACKUP                = FALSE
#   EXTERNAL_COPY                  = FALSE
#   EXTERNAL_RESTORE               = FALSE
#   FAST_RECOVER                   = 0
#   FF_ARCHIVE_NUM                 = 1
#   FF_BACKUP_ID                   = 31.12.2037 23:59:00
#   FF_RECOVER_NUM                 = 1
#   FF_SWITCH_NUM                  = 1
#   HIGH_COMPRESSION               = FALSE
#   INTERNAL_PASSWORD              =
#   LOGFORMAT                      = logarcKHVN.743803837.|.0f.1
#   MAKE_DB                        = FALSE
#   MIRROR_ARCHIVE_PATH            = /u02/oradata/khvn/archive
#   MIRROR_A_INTERFACE             = kkn-dbnode1-2351
#   MIRROR_B_INTERFACE             = kkn-dbnode1-2351
#   MIRROR_DBS_PATH                =
#   MIRROR_HOME                    = /u01/app/ora10/product/10.2.0/db_1
#   MIRROR_HOST                    = kkn-dbnode1-2351
#   MIRROR_INSTANCE                =
#   MIRROR_PASSWORD                =
#   MIRROR_RELEASE                 = 10.2.0.4.0
#   MIRROR_SID                     = KHVNS
#   MIRROR_USER                    =
#   NAME                           = KHVN1
#   ORACLE_HOME                    = /u01/app/ora10/product/10.2.0/db_1
#   ORACLE_RELEASE                 = 10.2.0.4.0
#   ORACLE_SID                     = KHVN
#   PARALLEL_ARCHIVER              = 0
#   PARALLEL_COPY                  = 4
#   RAW_DEVICE                     = FALSE
#   REAL_A_INTERFACE               = kkn-dbnode3-2351
#   REAL_B_INTERFACE               = kkn-dbnode3-2351
#   REAL_HOST                      = kkn-dbnode3-2351
#   RECOVER_CHECK_FILES            = 30
#   RECOVER_CONTINUE               = FALSE
#   RECOVER_DELAY                  = 240
#   RECOVER_DELETE                 = TRUE
#   RECOVER_LOSSLESS               = FALSE
#   RECOVER_MODE                   = TIME_DELAY
#   RECOVER_NUM                    = 131493
#   RECOVER_OPEN_READONLY          = FALSE
#   RECOVER_REDO_LOG_PATH          =
#   RECOVER_ROLLBACK               = FALSE
#   RECOVER_ROLLBACK_PATH          =
#   RECOVER_ROLLBACK_SIZE          =
#   RECOVER_START_CLEAR_LOGFILES   = FALSE
#   RECOVER_START_MAKE_DB          = FALSE
#   RECOVER_STATUS                 = RUN
#   RECOVER_STOP_COMPLETE          = TRUE
#   RECOVER_STOP_LOSSLESS          = FALSE
#   RECOVER_TO                     = 31.12.2099 23:59:00
#   RECOVER_TO_NUMBER              = 41284
#   RECOVER_VERIFY_STATUS          = STOP
#   RECOVER_VERIFY_SYNC            =
#   SAME_FS_PARALLEL               = TRUE
#   STANDBY                        = TRUE
#   STRUCTURE_CHANGE               = TRUE
#   STRUCTURE_CHECK_INTERVAL       = 60
#   STRUCTURE_CHECK_NOLOGGING      = TRUE
#   STRUCTURE_STATUS               = STOP
#   TRD_PASSWORD                   =
#
#   --------- CRON Check Mirror Files ----------
#   CRON[ 0] : 1000010 010000000000
#
#   -------------- Active Processes ----------
#   trdcopy        :
#   trdarchiver    :
#   trdrecover     : 2556268  22.05.2014 17:36:34  RUN
#   trdstructure   :
#
#   -------------- Statistic of Recover ------
#   Last update                  : 22.05.2014 17:36:34
#   Archive-Dir total            : 150 GB
#   Archive-Dir free             : 143 GB
#   Archive-Dir limit warning    : 70
#   Arshive-Dir limit error      : 90
#   Number of total files        : 18
#   Number logfiles recovered    : 1034
#   logfile-size recovered       : 123 GB
#   Average                      : 5 files/h
#   Average                      : 608 MB/h
#   Maximum                      : 14 files/h
#   Maximum                      : 2.4 GB/h
#   Current                      : 6 files/h
#   Current                      : 1.1 GB/h
#   Min. Rollback                :
#   State of mirror              : 22.05.2014 13:26:50
#   Max. Rollforward             :
#
#   -------------- Last Message --------------
#   recover 20140522172734OK      1212Recover of /u02/oradata/khvn/archive/logarcKHVN.743803837.131493.1 at 17:40 22.05.2014.
#

# .


def parse_libelle_business_shadow(string_table: StringTable) -> StringTable:
    return string_table


agent_section_libelle_business_shadow = AgentSection(
    name="libelle_business_shadow",
    parse_function=parse_libelle_business_shadow,
)


def check_libelle_business_shadow_to_mb(size: str) -> int:
    if size.endswith("MB"):
        return int(float(size.replace("MB", "")))
    if size.endswith("GB"):
        return int(float(size.replace("GB", ""))) * 1024
    if size.endswith("TB"):
        return int(float(size.replace("TB", ""))) * 1024 * 1024
    if size.endswith("PB"):
        return int(float(size.replace("PB", ""))) * 1024 * 1024 * 1024
    if size.endswith("EB"):
        return int(float(size.replace("EB", ""))) * 1024 * 1024 * 1024 * 1024
    return int(float(size))


# parses agent output into a dict
def check_libelle_business_shadow_parse(info: StringTable) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in info:
        if len(line) > 1 and line[0].startswith("Host   "):
            parsed["host"] = re.sub("^ +", "", line[1])
        elif len(line) > 2 and line[0].startswith("Start-Time   "):
            parsed["start_time"] = re.sub("^ +", "", line[1]) + ":" + line[2]
        elif len(line) > 1 and line[0] == "Release":
            parsed["release"] = re.sub("^ +", "", line[1])
        elif len(line) > 1 and line[0].startswith("Status   "):
            parsed["libelle_status"] = re.sub("^ +", "", line[1])
        elif len(line) > 3 and (
            line[0].startswith("trdrecover   ") or line[0].startswith("trdarchiver   ")
        ):
            parsed["process"] = re.sub(" +$", "", line[0])
            parsed["process_status"] = re.sub("^[0-9]+ +", "", line[3])
        elif len(line) > 1 and line[0].startswith("Archive-Dir total   "):
            parsed["arch_total_mb"] = check_libelle_business_shadow_to_mb(re.sub(" ", "", line[1]))
        elif len(line) > 1 and line[0].startswith("Archive-Dir free   "):
            parsed["arch_free_mb"] = check_libelle_business_shadow_to_mb(re.sub(" ", "", line[1]))
    return parsed


#   .--info----------------------------------------------------------------.
#   |                          _        __                                 |
#   |                         (_)_ __  / _| ___                            |
#   |                         | | '_ \| |_ / _ \                           |
#   |                         | | | | |  _| (_) |                          |
#   |                         |_|_| |_|_|  \___/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_libelle_business_shadow_info(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_libelle_business_shadow_info(section: StringTable) -> CheckResult:
    parsed = check_libelle_business_shadow_parse(section)
    message = "Libelle Business Shadow"
    if "host" in parsed:
        message += f", Host: {parsed['host']}"
    if "release" in parsed:
        message += f", Release: {parsed['release']}"
    if "start_time" in parsed:
        message += f", Start Time: {parsed['start_time']}"

    yield Result(state=State.OK, summary=message)


check_plugin_libelle_business_shadow_info = CheckPlugin(
    name="libelle_business_shadow_info",
    service_name="Libelle Business Shadow Info",
    sections=["libelle_business_shadow"],
    discovery_function=discover_libelle_business_shadow_info,
    check_function=check_libelle_business_shadow_info,
)

# .
#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_libelle_business_shadow_status(section: StringTable) -> DiscoveryResult:
    parsed = check_libelle_business_shadow_parse(section)
    if "libelle_status" in parsed:
        yield Service()


def check_libelle_business_shadow_status(section: StringTable) -> CheckResult:
    parsed = check_libelle_business_shadow_parse(section)
    if "libelle_status" in parsed:
        message = f"Status is: {parsed['libelle_status']}"
        state = State.OK if parsed["libelle_status"] == "RUN" else State.CRIT
    else:
        message = "No information about libelle status found in agent output"
        state = State.UNKNOWN

    yield Result(state=state, summary=message)


check_plugin_libelle_business_shadow_status = CheckPlugin(
    name="libelle_business_shadow_status",
    service_name="Libelle Business Shadow Status",
    sections=["libelle_business_shadow"],
    discovery_function=discover_libelle_business_shadow_status,
    check_function=check_libelle_business_shadow_status,
)

# .
#   .--process-------------------------------------------------------------.
#   |                                                                      |
#   |                  _ __  _ __ ___   ___ ___  ___ ___                   |
#   |                 | '_ \| '__/ _ \ / __/ _ \/ __/ __|                  |
#   |                 | |_) | | | (_) | (_|  __/\__ \__ \                  |
#   |                 | .__/|_|  \___/ \___\___||___/___/                  |
#   |                 |_|                                                  |
#   '----------------------------------------------------------------------'


def discover_libelle_business_shadow_process(section: StringTable) -> DiscoveryResult:
    parsed = check_libelle_business_shadow_parse(section)
    if "process" in parsed:
        yield Service()


def check_libelle_business_shadow_process(section: StringTable) -> CheckResult:
    parsed = check_libelle_business_shadow_parse(section)
    if "process" in parsed:
        message = f"Active Process is: {parsed['process']}, Status: {parsed['process_status']}"
        state = State.OK if parsed["process_status"] == "RUN" else State.CRIT
    else:
        message = "No Active Process found!"
        state = State.CRIT

    yield Result(state=state, summary=message)


check_plugin_libelle_business_shadow_process = CheckPlugin(
    name="libelle_business_shadow_process",
    service_name="Libelle Business Shadow Process",
    sections=["libelle_business_shadow"],
    discovery_function=discover_libelle_business_shadow_process,
    check_function=check_libelle_business_shadow_process,
)

# .
#   .--archive dir---------------------------------------------------------.
#   |                          _     _                 _ _                 |
#   |            __ _ _ __ ___| |__ (_)_   _____    __| (_)_ __            |
#   |           / _` | '__/ __| '_ \| \ \ / / _ \  / _` | | '__|           |
#   |          | (_| | | | (__| | | | |\ V /  __/ | (_| | | |              |
#   |           \__,_|_|  \___|_| |_|_| \_/ \___|  \__,_|_|_|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_libelle_business_shadow_archive_dir(section: StringTable) -> DiscoveryResult:
    parsed = check_libelle_business_shadow_parse(section)
    if "arch_total_mb" in parsed and "arch_free_mb" in parsed:
        yield Service(item="Archive Dir")


def check_libelle_business_shadow_archive_dir(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    parsed = check_libelle_business_shadow_parse(section)
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=[(item, parsed["arch_total_mb"], parsed["arch_free_mb"], 0)],
    )


check_plugin_libelle_business_shadow_archive_dir = CheckPlugin(
    name="libelle_business_shadow_archive_dir",
    service_name="Libelle Business Shadow %s",
    sections=["libelle_business_shadow"],
    discovery_function=discover_libelle_business_shadow_archive_dir,
    check_function=check_libelle_business_shadow_archive_dir,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

# .
