# This file is managed via WATO, do not edit manually or you
# lose your changes next time when you update the agent.

# Connection and authentication
$DBUSER = @("c##checkmk", "********", "", "localhost", "1521")
$DBUSER_XE1 = @("/", "", "", "", "")
$DBUSER_XE2 = @("xe2user", "xe2pwd", "SYSDBA", "localhost1", "1521")
$ASMUSER = @("/", "", "SYSASM", "", "")

# Sections to run in foreground and wait for the result
$SYNC_SECTIONS = @("instance", "performance", "processes", "sessions", "longactivesessions", "logswitches", "undostat", "recovery_area", "recovery_status", "dataguard_stats", "locks")

# Sections to run in the background, at a slower interval cached
$ASYNC_SECTIONS = @("tablespaces", "rman", "jobs", "resumable")

# Sections to run in foreground for ASM
$SYNC_ASM_SECTIONS = @("instance", "processes")

# Sections to run in the background for ASM
$ASYNC_ASM_SECTIONS = @("asm_diskgroup")

# Cache time (i.e. check interval) for async sections
$CACHE_MAXAGE = 601

# Only monitor the following SIDs (if found)
$ONLY_SIDS = @("XE1", "XEXE")

# Skip the following SIDs (if found)
$SKIP_SIDS = @("XE2")

# Do not monitor the following SIDs at all
$EXCLUDE_AAA = "ALL"
$EXCLUDE_BBB = "ALL"
$EXCLUDE_CCC = "jobs"
