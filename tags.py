



with open("tags.txt", "r") as tfile:
    content = tfile.readlines()
from collections import defaultdict
tags = defaultdict(int)
for tag in content:
    if "/" in tag:
        continue
    tags[tag] += 1

for tag, count in tags.iteritems():
    print tag, count


