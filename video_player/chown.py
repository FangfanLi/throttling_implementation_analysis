import os
import sys

if len(sys.argv) != 2:
    sys.exit(-1)
else:
    target_dir = sys.argv[1]

uid = int(os.geteuid())
gid = int(os.getegid())
for root, dirs, files in os.walk(target_dir):
    for dir in dirs:
        os.chown(os.path.join(root, dir), 501, 20)
    for file in files:
        os.chown(os.path.join(root, file), 501, 20)
