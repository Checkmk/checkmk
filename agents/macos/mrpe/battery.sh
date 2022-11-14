#! /bin/bash
# battery and charger support
ChargerWattage=$(pmset -g ac | awk -F" " '/Wattage/ {print $3}' | tr -d -c '[:digit:]')
[ "X${ChargerWattage}" = "X" ] || ChargerInfo=", ${ChargerWattage}W charger connected"
CheckBatteryHealth() {
        system_profiler SPPowerDataType | egrep "Cycle Count|Condition|Maximum Capacity|Charge Remaining|^      Serial Number" | sed -e 's/:\ /=/' -e 's/          //' | while read ; do
                case ${REPLY%=*} in
                        Charge*)
                                printf " charge_remaining=${REPLY##*=}"
                                ;;
                        Maximum*)
                                printf " maximum_capacity=$(tr -d -c '[:digit:]' <<<${REPLY##*=})"
                                ;;
                        Cycle*)
                                printf " cycle_count=${REPLY##*=}"
                                ;;
                        Condition)
                                if [ "X${REPLY##*=}" = "XNormal" ]; then
                                        printf " condition=0"
                                elif [ "X${REPLY##*=}" = "XService Recommended" ]; then
                                        printf " condition=1"
                                else
                                        # fallback for either "Service Battery" or whatever other condition
                                        # Apple already defined or will define in the future.
                                        printf " condition=2"
                                fi
                                ;;
                        *Serial*)
                                ObfuscatedChagerSerial=$(tr -d -c '[:digit:]' <<<"${REPLY##*=}")
                                printf " charger_serial=${ObfuscatedChagerSerial:-0}"
                                ;;
                esac
        done
} # CheckBatteryHealth

BatteryHealthGraph=$(CheckBatteryHealth)
case ${BatteryHealthGraph} in
        *condition=2*)
                OKState="CRIT"
                BatteryHealth=", battery condition: $(system_profiler SPPowerDataType | awk -F": " '/Condition/ {print $2}')"
                ;;
        *condition=1*)
                OKState="WARN"
                BatteryHealth=", battery condition: Service Recommended"
                ;;
        *)
                OKState="OK"
                ;;
esac
# check battery itself
pmset -g batt | grep "InternalBattery" | while read ; do
        SensorName=$(awk -F" " '{print $1}' <<<${REPLY} | tr -d -c '[:alnum:]')
        GraphName=$(tr '[:upper:]' '[:lower:]' <<<${SensorName})
        Percentage=$(awk -F";" '{print $1}' <<<${REPLY} | awk -F" " '{print $3}' | tr -d -c '[:alnum:]')
        BattStatus=$(awk -F";" '{print $2}' <<<${REPLY})
        VerboseOutput=$(awk -F";" '{print $3}' <<<${REPLY} | sed 's/\ present/, battery present/')
        case ${VerboseOutput} in
                *"not charging"*)
                        OKState="WARN"
                        ;;
        esac
        Remaining=$(awk -F" " '{print $1}' <<<${VerboseOutput})
        [ "X${Remaining}" = "X" -o "X${Remaining}" = "X(no" ] || RemainingMinutes=$(( $(( ${Remaining%:*} * 60 )) + ${Remaining##*:} ))
        if [ ${Percentage} -le 10 ]; then
                CheckStatus="CRIT"
        elif [ ${Percentage} -le 25 ]; then
                CheckStatus="WARN"
        else
                CheckStatus="${OKState}"
        fi
echo "${SensorName} ${Percentage}%${BattStatus},${VerboseOutput}${BatteryHealth}${ChargerInfo} | ${GraphName}_percentage=${Percentage:-0} remaining_minutes=${RemainingMinutes:-0} charger_power=${ChargerWattage:-0}${BatteryHealthGraph}"
done

case ${CheckStatus} in
  "OK")   exit 0;;
  "WARN") exit 1;;
  "CRIT") exit 2;;
esac

