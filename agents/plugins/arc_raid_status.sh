#cli64 can be found at:
# ftp://ftp.areca.com.tw/RaidCards/AP_Drivers/Linux/CLI/

echo "<<<arc_raid_status>>>"
cli64 rsf info | tail -n +3 | head -n -2
