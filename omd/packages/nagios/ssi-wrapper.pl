#!/usr/bin/perl
##
## Site speicific SSI wrapper
##
use File::Basename;
$ssi = basename($0);
@site = split(/\//, $ENV{'SCRIPT_NAME'});
$file = sprintf("/opt/omd/sites/%s/etc/nagios/ssi/%s", $site[1], $ssi);
if( -x $file ){
    open (FH, '-|', $file);
    while(<FH>){
        print;
    }
    exit 0;
}
if( -e $file ){
    open (FH, $file);
    while(<FH>){
        print;
    }
    exit 0;
}
exit 0;
