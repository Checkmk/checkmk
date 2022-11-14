#! /bin/bash

export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/sbin

VMStatOutput="$(vm_stat | sed 's/\.$//')"
pagesize=$(awk '/Mach/ {print $8}' <<<"${VMStatOutput}")

# compressedpages=$(awk '/stored in compressor:/ {print $5}' <<<"${VMStatOutput}")
# occupiedpages=$(awk '/occupied by compressor:/ {print $5}' <<<"${VMStatOutput}")
MemTotal=$(sysctl -n hw.memsize)
SwapTotal=$(( ${MemTotal} * 3 ))
MemFree=$(( $(( $(awk '/speculative:/ {print $3}' <<<"${VMStatOutput}") + $(awk '/inactive:/ {print $3}' <<<"${VMStatOutput}") + $(awk '/free:/ {print $3}' <<<"${VMStatOutput}") )) * $pagesize ))
SwapSize="$(sysctl -n vm.swapusage | sed 's/,/./g' | awk -F"used = " '{print $2}' | cut -f1 -d' ')"
case ${SwapSize} in
        *K)
                SwapUsed=$(sed 's/K//' <<< "${SwapSize}" | awk '{print $1*1024}')
                ;;
        *M)
                SwapUsed=$(sed 's/M//' <<< "${SwapSize}" | awk '{print $1*1048576}')
                ;;
        *G)
                SwapUsed=$(sed 's/G//' <<< "${SwapSize}" | awk '{print $1*1073741824}')
                ;;
esac


# Report whole vm_stat output as 'Swap and Paging' sensor to really get all
# the details and to decide how much memory is enough, see for example
# https://github.com/ThomasKaiser/Knowledge/blob/master/articles/Exploring_Apple_Silicon_on_MacBookAir10.md#testing-different-hardware-configurations-on-the-same-machine
Parse_Full_VM_Stat_Output() {
        # this will result in 24 graphs for this sensor
        grep -v Mach <<<"${VMStatOutput}" | sed 's/"//g' | while read ; do
                Attribute="$(awk -F":" '{print $1}' <<<"${REPLY}" | tr '[:upper:]' '[:lower:]' | sed 's/\ /_/g')"
                Value=$(( $(awk -F":" '{print $2}' <<<"${REPLY}") / ${ScaleFactor} ))
                printf " ${Attribute}=${Value}"
        done
} # Parse_Full_VM_Stat_Output
ParseVM_Stat_Output() {
        # this will limit the count of graphs to the reasonable ones to understand 
        # 'Is the machine's memory too low?'
        egrep "free|zero|ompre|ins:|outs:" <<<"${VMStatOutput}" | sed 's/"//g' | while read ; do
                Attribute="$(awk -F":" '{print $1}' <<<"${REPLY}" | tr '[:upper:]' '[:lower:]' | sed 's/\ /_/g')"
                Value=$(( $(awk -F":" '{print $2}' <<<"${REPLY}") / ${ScaleFactor} ))
                printf " ${Attribute}=${Value}"
        done
} # ParseVM_Stat_Output
# report values in MB instead of pages (pagesize might change between OS releases)
ScaleFactor=$(( 1048576 / ${pagesize} ))
VMStatGraph=$(ParseVM_Stat_Output)
SwapfilePrefix="$(sysctl -n vm.swapfileprefix)"
CountOfSwapFiles=$(ls "${SwapfilePrefix}"* 2>/dev/null | wc -l | tr -d -c '[:digit:]')
VMStatus="${CountOfSwapFiles} swapfile(s)"
MemoryPressure=$(sysctl -n vm.memory_pressure)
RunningApps="$(ps auxw -o rss,vsz,command)"
AllApps=$(grep "/Applications/" <<<"${RunningApps}" | grep -c MacOS)
grep -q Safari <<<"${RunningApps}" && RAMSafari=$(( $(grep Safari <<<"${RunningApps}" | awk -F" " '{sum+=$6;} END{print sum;}') / 1024 ))
grep -q Chrome <<<"${RunningApps}" && RAMChrome=$(( $(grep Chrome <<<"${RunningApps}" | awk -F" " '{sum+=$6;} END{print sum;}') / 1024 ))
grep -q Firefox <<<"${RunningApps}" && RAMFF=$(( $(grep Firefox <<<"${RunningApps}" | awk -F" " '{sum+=$6;} END{print sum;}') / 1024 ))

echo "${VMStatus} | memory_pressure=${MemoryPressure:-0} swapfiles=${CountOfSwapFiles:-0} all_apps=${AllApps:-0} safari_ram=${RAMSafari:-0} firefox_ram=${RAMFF:-0} chrome_ram=${RAMChrome:-0}${VMStatGraph}"

exit 0

