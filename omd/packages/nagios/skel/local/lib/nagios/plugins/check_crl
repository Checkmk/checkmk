#!/usr/bin/python3

# Remy van Elst - raymii.org - 2012 
# 05.11.2012
# Changelog: - check with hours instead of dates for more precision,
#            - URL errors are now also catched as nagios exit code.

# Michele Baldessari - Leitner Technologies - 2011
# 23.08.2011

import datetime
import getopt
import os
import pprint
import subprocess
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error

def check_crl(url, warnhour, crithour):
    tmpcrl = tempfile.mktemp("crl")
    #request = urllib.request.urlretrieve(url, tmpcrl)
    try:
        urllib.request.urlretrieve(url, tmpcrl)
    except:
        print ("CRITICAL: CRL could not be retreived: %s" % url)
        sys.exit(2)

    ret = subprocess.check_output(["/usr/bin/openssl", "crl", "-inform", "DER", "-noout", "-nextupdate", "-in", tmpcrl])
    nextupdate = ret.strip().decode('utf-8').split("=")
    os.remove(tmpcrl)
    eol = datetime.datetime.strptime(nextupdate[1],"%b %d %H:%M:%S %Y GMT")
    today = datetime.datetime.now()
    delta = eol - today
    deltaseconds = delta.seconds + delta.days * 86400
    expdays = delta.days
    exphours = delta.seconds // 3600
    hours = deltaseconds // 3600
    if  hours > crithour and hours <= warnhour:
        msg = "WARNING CRL Expires in %s hours (%s days) (on %s)" % (hours, expdays, eol)
        exitcode = 1
    elif hours < crithour:
        msg = "CRITICAL CRL Expires in %s hours (%s  days ) (on %s)" % (hours, expdays, eol)
        exitcode = 2
    else:
        msg = "OK CRL Expires in %s hours (%s days) (on %s)" % (hours, expdays, eol)
        exitcode = 0

    print (msg)
    sys.exit(exitcode)

def usage():
    print ("check_crl.py -h|--help -v|--verbose -u|--url=<url> -w|--warninghours=<hours> -c|--criticalhours=<hours>")
    print ("Example, if you want to get a warning if a CRL expires in 24 hours and a critical if it expires in 12 hours:")
    print ("./check_crl.py -u \"http://domain.tld/url/crl.crl\" -w 24 -c 12")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:w:c:", ["help", "url=", "warninghours=", "criticalhours="])
    except getopt.GetoptError as err:
        usage()
        sys.exit(2)
    url = None
    warningdays = None
    criticaldays = None
    warninghours = None
    criticalhours = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-u", "--url"):
            url = a
        elif o in ("-w", "--warninghours"):
            warninghours = a
        elif o in ("-c", "--criticalhours"):
            criticalhours = a
        else:
            assert False, "unhandled option"

    if url != None and warninghours != None and criticalhours != None:
        check_crl(url, int(warninghours), int(criticalhours))
    else:
        usage()
        sys.exit(2) 


if __name__ == "__main__":
    main()