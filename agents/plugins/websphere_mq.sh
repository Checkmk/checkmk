# plugin for websphere_mq_* checks

if [ "$1" = "" ]
then
    su - mqm -c "/usr/lib/check_mk_agent/plugins/websphere_mq.sh run"
else
    # Loop over all local mq instances
    for QM in $( ps -ef  | grep -i '[/]usr/mqm/bin/runmqchl -c' | awk '{ print $NF }' | uniq)
    do
         echo '<<<websphere_mq_channels>>>'
         for i in `echo " display CHANNEL (*) TYPE (SDR) " | /usr/bin/runmqsc $QM | grep CHLTYPE | grep -v SYSTEM | awk '{print $1}'`
         do
           j=`echo "display $i " | /usr/bin/runmqsc $QM | grep XMITQ | tr " " "\n" | grep XMITQ | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }'`
           a=`echo " display qlocal ($j) CURDEPTH " | /usr/bin/runmqsc $QM | grep CURDEPTH | tr " " "\n" | grep CURDEPTH | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }' | tr "\n" " "`
           c=`echo " display qlocal ($j) MAXDEPTH  " | /usr/bin/runmqsc $QM | grep MAXDEPTH | tr " " "\n" | grep MAXDEPTH | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }' | tr "\n" " "`

           l=`echo $i | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }'`
           s=`echo " display chstatus($l)" | /usr/bin/runmqsc $QM | grep STATUS | tail -1 | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $NF }'`

           if [ "$s" = "" ]
           then
             s="Unknown"
           fi
           echo "$a  $i $c $s"
         done
         echo '<<<websphere_mq_queues>>>'
         for t in `echo " display queue (*) where (USAGE EQ NORMAL) " | /usr/bin/runmqsc $QM | grep QLOCAL | grep -v SYSTEM | grep -v _T0 |  grep -v _T1 |  grep -v _T2 | grep -v _T3 | grep -v mqtest | grep QUEUE | awk '{ print $1 }' | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }'`
         do
           a=`echo " display queue ($t) CURDEPTH " | /usr/bin/runmqsc $QM | grep CURDEPTH | tail -1 | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }'`
           b=`echo " display qlocal ($t) MAXDEPTH  " | /usr/bin/runmqsc $QM | grep MAXDEPTH | tr " " "\n" | grep MAXDEPTH | sed '1,$s/(/ /g' | sed '1,$s/)/ /g'| awk '{print $2 }' | tr "\n" " "`

          # Muster: Anzahl eingehender Messages $a auf $t Max-Queues $b

           echo "$a $t $b"
         done
     done
fi
