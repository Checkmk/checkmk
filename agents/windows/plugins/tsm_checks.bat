@echo off
set CMK_VERSION="2.0.0p22"
cd C:\Progra~1\Tivoli\TSM\baclient\
SET COMMAND=dsmadmc -dataonly=YES -id=admin -password=password -displaymode=table

echo ^<^<^<tsm_drives^>^>^>
%COMMAND% "select 'default', library_name, drive_name, drive_state, online, drive_serial from drives"

echo ^<^<^<tsm_paths^>^>^>
%COMMAND% "select source_name, destination_name, online from paths"

echo ^<^<^<tsm_sessions^>^>^>
%COMMAND% "select session_id, client_name, state, wait_seconds from sessions"

echo ^<^<^<tsm_scratch^>^>^>
%COMMAND% "select 'default', count(library_name), library_name from libvolumes where status='Scratch' group by library_name"

echo ^<^<^<tsm_storagepools^>^>^>
%COMMAND% "select 'default', type, stgpool_name, sum(logical_mb) from occupancy group by type, stgpool_name"

echo ^<^<^<tsm_stagingpools^>^>^>
%COMMAND% "select 'default', stgpool_name, pct_utilized from volumes where access='READWRITE' and devclass_name<>'DISK'"
