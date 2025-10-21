# Oracle SQL check

## Oracle instant client download and installation

### Linux

Please, download and  unzip Oracle Instant Client installation for Linux.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

We recommend to use version 21.

For unzipping, use command like this:
assuming that you are using `instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip`
1. Global Installation
```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /opt/oracle-instant-client
```
or
2. In Agent installation
```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /path/to/agent/plugins/packages/mk-oracle
```
Please install oracle instant client to be write-accessible only by admin user.

After the Instant Client libraries are installed you may use WATO to configure type of deployment

### Windows

Download and unzip  Oracle Windows installation guide to configure your Oracle Instant Client in folder of your choice.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

Verify the following:
1. Global Installation
PATH must contain the path to the folder where dlls are stored.
For example: `C:\oracle\instantclient_21_3`
2. In Agent Installation
you unzip *.dll files to `%PROGRAMDATA%/checkmk/agent/plugins/packages/mk-oracle` folder.

After the Instant Client libraries are installed you may use WATO to configure type of deployment






