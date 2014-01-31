<?php
 # This is a simple wrapper who call's the check_mk_agent,
 # to use with curl as datasource program
 # May consider using sudo here.
 system("/usr/bin/check_mk_agent")

?>
