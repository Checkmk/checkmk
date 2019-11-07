# Simple python script to find that file line ending is correctly encoded
# Very Simple.

import os

with open("install\\resources\\check_mk.user.yml", "rb") as f:
    content = f.read()
    if content.count("\r\n") < 10:
        exit(1)

exit(0)
