# Requirements for testing locally
```
pip3 install ansible
pip3 install boto
```

## export required variables e.g.:
```
export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID_FROM_CSV_FILE>
export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY_CSV_FILE>
export EC2_KEY=<KEYNAME>
export ANSIBLE_SSH_PRIVATE_KEY_FILE=<PATH_TO_PEM_FILE>
export CMKADMIN_PASS=<CMKADMIN_PASS>
export EDITION=enterprise
export CMK_VERS=<VERSION>
export PACKAGE_DIR=<PATH_TO_DIRECTORY_OF_CHECKMK_DEB_FILE>
```

## execute:
```
./build_ami.yml
```
