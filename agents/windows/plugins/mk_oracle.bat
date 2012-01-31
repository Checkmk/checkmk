@echo off
echo ^<^<^<oracle_sessions^>^>^>
(echo.|set /p x=%ORACLE_SID%)
(
echo set cmdsep on
echo set cmdsep '"'; --"
echo "set pages 0"
echo "set feedback off"
echo "set head off"
echo "select count(*) from v$session where status = 'ACTIVE';"
) | sqlplus -S / as sysdba


echo ^<^<^<oracle_logswitches^>^>^>
(echo.|set /p x=%ORACLE_SID%)
(
echo set cmdsep on
echo set cmdsep '"'; --"
echo "set pages 0"
echo "set feedback off"
echo "set head off"
echo "select count(*) from v$loghist where first_time > sysdate - 1/24;"
) | sqlplus -S / as sysdba



echo ^<^<^<oracle_tablespaces^>^>^>
(
echo set cmdsep on
echo set cmdsep '"'; --"
echo "set pages 0"
echo "set linesize 900"
echo "set tab off"
echo "set feedback off"
echo "set head off"
echo "column instance format a10"
echo "column file_name format a100"
echo "select f.file_name, f.tablespace_name, f.status, f.AUTOEXTENSIBLE, f.blocks, f.maxblocks, f.USER_BLOCKS, f.INCREMENT_BY, f.ONLINE_STATUS, t.BLOCK_SIZE, t.status, decode(sum(fs.blocks), NULL, 0, sum(fs.blocks)) free_blocks from dba_data_files f, dba_tablespaces t, dba_free_space fs where f.tablespace_name = t.tablespace_name and f.file_id = fs.file_id(+) group by f.file_name, f.tablespace_name, f.status, f.autoextensible, f.blocks, f.maxblocks, f.user_blocks, f.increment_by, f.online_status, t.block_size, t.status UNION select f.file_name, f.tablespace_name, f.status, f.AUTOEXTENSIBLE, f.blocks, f.maxblocks, f.USER_BLOCKS, f.INCREMENT_BY, 'TEMP', t.BLOCK_SIZE, t.status, 0 from dba_temp_files f, dba_tablespaces t where f.tablespace_name = t.tablespace_name;"
) | sqlplus -S / as sysdba

echo ^<^<^<oracle_version^>^>^>
REM (echo %ORACLE_SID%)
(echo.|set /p x=%ORACLE_SID% )
(
echo set cmdsep on
echo set cmdsep '"'; --"
echo "set pages 0"
echo "set feedback off"
echo "set head off"
echo "select * from v$version;"
) | sqlplus -S / as sysdba
