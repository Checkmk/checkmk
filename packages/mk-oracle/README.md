# Oracle SQL check

## Oracle instant client download and installation

### Linux

Please, download and unzip Oracle Instant Client _zipped_ installation for your Linux.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

We recommend to use version 21.

For unzipping, use command like this:
assuming that you are using `instantclient-basiclite-linux.x64-21.20.0.0.0dbru.zip`
Choose one of the following options:

1. Global Installation

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /opt/checkmk/oracle-instant-client
```

2. In Agent installation(recommended)

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /path/to/agent/plugins/packages/mk-oracle
```

For default _legacy deployment_ plugins path for Checkmk agent on Linux is `/usr/lib/check_mk_agent/plugins/`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /usr/lib/check_mk_agent/plugins/packages/mk-oracle/
```

For default _single directory deployment_ plugins path for Checkmk agent on Linux is `/opt/checkmk/agent/default/package/plugins`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /opt/checkmk/agent/default/package/plugins/packages/mk-oracle/
```

you may determine the path to the agent installation by running command:

```
sudo check_mk_agent | grep "^pluginsdir " | head -1
```

Please install oracle instant client to be write-accessible only by admin user.

After the Instant Client libraries are installed you may use WATO to configure type of deployment

### Windows

Download and unzip Oracle Windows installation guide to configure your Oracle Instant Client in folder of your choice.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

Choose one of the following options:

1. Global Installation
   PATH must contain the path to the folder where dlls are stored.
   For example: `C:\oracle\instantclient_21_3`
2. In Agent Installation(recommended)
   you unzip \*.dll files to `PROGRAMDATA%/checkmk/agent/plugins/packages/mk-oracle` folder.
