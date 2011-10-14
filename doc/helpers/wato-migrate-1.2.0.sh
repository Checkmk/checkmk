#!/bin/bash
set -e

if [ ! -e main.mk -o ! -e conf.d ]
then
    echo "You are probably not in the etc/check_mk. I cannot find"
    echo "main.mk nor conf.d."
    exit 1
fi

echo "Making backup of conf.d into $TAR"
TAR=conf.d-$(date +%s).tar.gz
tar czf $TAR conf.d

cd conf.d

if which tree > /dev/null
then
    echo "Before migration:"
    echo "-----------------------------------------"
    tree
    echo "-----------------------------------------"
fi

find * -name "*.mk.wato" | while read line
do
    thedir=${line%/*}
    thefile=${line##*/}
    echo "Moving $thefile in $thedir..."
    newdir="wato/${thefile%.mk.wato}"
    mkdir -vp "$newdir"
    mv -v "$line" "$newdir/.wato"
    mv -v "${line%.wato}" "$newdir/hosts.mk"
done

# No move also the empty WATO directories
find * -name ".wato" | while read line
do
    if [ ${line:0:7} = ./wato/ ] ; then continue ; fi
    thedir=${line%/*}
    thefile=${line##*/}
    echo "Moving empty directory $thedir..."
    mkdir -p "wato/$thedir"
    mv -v $line "wato/$thedir"
    rmdir -v "$thedir" 2>/dev/null || true
done

    
if which tree > /dev/null
then
    echo "-----------------------------------------"
    echo "After migration:"
    echo "-----------------------------------------"
    tree
fi


