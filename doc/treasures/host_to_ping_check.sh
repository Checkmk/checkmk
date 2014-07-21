find . -name _HOST_\*  | sed -re 's/(\S*)_HOST_(\S*)/\1_HOST_\2 \1PING\2/' | xargs -n 2 cp
