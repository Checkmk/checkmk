#!/bin/bash
echo "<<<storcli_pdisks>>>"
/opt/MegaRAID/storcli/storcli64 /call/eall/sall show
echo "<<<storcli_vdrives>>>"
/opt/MegaRAID/storcli/storcli64 /call/vall show