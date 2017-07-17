#!/bin/bash
level=""
setlevel=0
logvalid=0
level_str=""
if [ -f "/opt/Navisphere/bin/setlevel.log" ]; then
	level=`cat /opt/Navisphere/bin/setlevel.log|head -1|cut -d' ' -f1`
	if [ $level == "medium" -o  $level == "low" ]; then
		logvalid=1
	fi
fi
rm /opt/Navisphere/bin/setlevel.log > /dev/null 2>&1
if [ ! -f "/opt/Navisphere/seccli/CST/certConfig.key" -a ! -f "/opt/Navisphere/seccli/CST/certConfig.security" ]; then
	setlevel=1

elif [ -f "/opt/Navisphere/seccli/CST/certConfig.key" -a -f "/opt/Navisphere/seccli/CST/certConfig.security" ]; then
	if [ $logvalid -eq 1 ]; then
		echo "The certificate verify level has been set in the previous install as $level, would you like to keep it(yes|no|y|n) ?"
		read prelevel < /dev/tty
	    case $prelevel in
    	"no"|"n")
        	echo "Removing previous install certificate verify level"
		    rm /opt/Navisphere/seccli/CST/certConfig.key >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1 
        	rm /opt/Navisphere/seccli/CST/certConfig.security >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
            setlevel=1
	        true
        	;;
		"yes"|"y")
			level_str=$level
			echo "The certificate verify level of previous install $level is set"
			STATUS=$?
        	true
	       	;;
	   	*)
			echo $level  >> /opt/Navisphere/bin/setlevel.log 2>&1
		    echo "The certificate verify level of previous install $level is set"
			STATUS=$?
            true
		    ;;	
	    esac
	else
		rm /opt/Navisphere/seccli/CST/certConfig.key >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
		rm /opt/Navisphere/seccli/CST/certConfig.security >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
		setlevel=1
	fi
else
	if [ -f "/opt/Navisphere/seccli/CST/certConfig.key" -a ! -f "/opt/Navisphere/seccli/CST/certConfig.security" ]; then
		rm /opt/Navisphere/seccli/CST/certConfig.key >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
        setlevel=1
    elif [ -f "/opt/Navisphere/seccli/CST/certConfig.security" -a ! -f "/opt/Navisphere/seccli/CST/certConfig.key" ]; then
        rm /opt/Navisphere/seccli/CST/certConfig.security >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
        setlevel=1
    else
        setlevel=0
    fi
fi
if [ $setlevel -eq 1 ]; then
	export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/Navisphere/lib/seccli
    export NAVI_SECCLI_CONF=/opt/Navisphere/seccli
    echo "Please enter the verifying level(low|medium|l|m) to set? "
    read level < /dev/tty
    case $level in
    "low"|"l")
	     echo "Setting low verifying level....."
	     echo ""
		 level_str="low"
         /opt/Navisphere/bin/naviseccli security -certificate -setLevel low  >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
		 STATUS=$?
         true
         ;;
     "medium"|"m")
         echo "Setting medium verifying level....."
		 echo ""
		 level_str="medium"
         /opt/Navisphere/bin/naviseccli security -certificate -setLevel medium >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
		 STATUS=$?
         true
         ;;
     *)
         echo "Setting (default) medium verifying level....."
         echo ""
	  	 level_str="medium"
         /opt/Navisphere/bin/naviseccli security -certificate -setLevel medium >> /opt/Navisphere/bin/setlevel.log.tmp 2>&1
	   	 STATUS=$?
         true
         ;;
    esac
fi

if [ $STATUS -eq 0 ]; then
	echo $level_str  >> /opt/Navisphere/bin/setlevel.log
	if [ -f "/opt/Navisphere/bin/setlevel.log.tmp" ]; then
		cat /opt/Navisphere/bin/setlevel.log.tmp >> /opt/Navisphere/bin/setlevel.log 2>&1
		rm /opt/Navisphere/bin/setlevel.log.tmp  > /dev/null 2>&1
	fi
    echo "Verification level $level_str has been set SUCCESSFULLY!!!"
else
    echo "Setting Verification level $level_str FAILED."
    if [ -f "/opt/Navisphere/bin/setlevel.log.tmp" ]; then
        cat /opt/Navisphere/bin/setlevel.log.tmp >> /opt/Navisphere/bin/setlevel.log 2>&1
        rm /opt/Navisphere/bin/setlevel.log.tmp  > /dev/null 2>&1
    fi
    echo "Please refer the log /opt/Navisphere/bin/setlevel.log "
fi
exit 0



