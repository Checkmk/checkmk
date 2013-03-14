@echo off
echo ^<^<^<wmic_process:sep^(44^)^>^>^>
wmic process get name,pagefileusage,virtualsize,workingsetsize,usermodetime,kernelmodetime,ThreadCount /format:csv
