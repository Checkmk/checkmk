[[official-check_mk-raw-edition-container]]
Official Check_MK Raw Edition Container
---------------------------------------

This is the official container of Check_MK. Check_MK is a leading tool
for Infrastructure & Application Monitoring. Simple configuration,
scaleable, flexible. Open Source and Enterprise.

Features of these containers:

* Each container manages a single site
* Containers of all Check_MK Editions can be built
* No internet connection is needed during container creation / update
* No special container privilege level required
* Clean update procedure

[[quick-start]]
Quick start
~~~~~~~~~~~

You can start a Check_MK container like this:

....
docker container run -dit -p 8080:5000 --tmpfs /omd/sites/cmk/tmp -v /omd/sites --name monitoring -v /etc/localtime:/etc/localtime --restart always checkmk/check-mk-enterprise:1.5.0p5
....

The Check_MK GUI should now be reachable via
`http://localhost:8080/cmk/check_mk/`.

The initial password of the initial administrative account `cmkadmin`
will be written to the container logs (see
`docker container monitoring logs`). You can customize this during
container creation if you like, see below.

Details about the arguments used above:

[cols="20%,80%",options="header",]
|=======================================================================
|Argument |Description
|`-p 8080:5000` |The sites web server listens on port 5000 by default. With this
                 example it is opened at port 8080 of the node. You may also use
                 port 80 here in case you don't have another process listening on
                 it. For more flexible options or HTTPS have a look below
|`--tmpfs /omd/sites/cmk/tmp` | For best performance you should mount a
tmpfs at the sites `tmp` directory. In case you rename you site ID (see
below for details), you will have to change this path.
|`-v /omd/sites` |
This makes all site data be persisted even when the container is
destroyed. In case you don't use this you will loose all you
configuration and monitoring data.
|`--name monitoring` | The name of the container. It must be unique per docker node. All examples below use
this name. In case you change this you will have to use your custom name
e.g. during update.
|`-v /etc/localtime:/etc/localtime` | Make the container use the same local time (timezone) config as your docker node.
|`--restart always` | Always restart the container if it stops.
|=======================================================================

[[use-packages-from-our-website]]
Use packages from our Website
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may want to use the officially released images from your website,
which you can find on the download page of each version as of version
1.5.0p5.

Download the file to your docker node and execute the load command:

....
docker load -i ~/Downloads/check-mk-enterprise-docker-1.5.0p5.tar.gz
....

After a successful import you can start creating containers using the
image `checkmk/check-mk-enterprise:1.5.0p5`.

[[listen-on-http-https-standard-ports]]
Listen on HTTP / HTTPS standard ports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a simple setup where Check_MK is the only web server on a
node you may use `-p 80:5000` instead of `-p 8080:5000`.

In most cases, where you have multiple web server running in different
containers you should use a reverse proxy which listens on port 80 and
distributes the request to the different containers. This can be done
using a nginx container.

This is also the recommended setup in case you want to serve your GUI
via HTTPS. The HTTPS termination should be done by the reverse proxy
container while the Check_MK containers still speak plain HTTP to the
reverse proxy.

[[set-initial-cmkadmin-password]]
Set initial cmkadmin password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During container creation you may add `-e CMK_PASSWORD='my#secret'` to
the command line to set the initial password of `cmkadmin` to
`my#secret`.

[[customizing-the-check_mk-site-id]]
Customizing the Check_MK site ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The container normally uses the site ID `cmk`. If you create a
distributed setup you need to use different site IDs for the involved
Check_MK sites. You may also set custom site IDs for other reasons. Add
`-e CMK_SITE_ID=mysite` to change the site ID.

[[sending-mail-notifications]]
Sending mail notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~

In most cases you want the Check_MK server to send mail notifications.
To make this possible you need to point the containers local MTA to your
mail relay. Add `-e MAIL_RELAY_HOST='mailrelay.mydomain.com'` to the
command line to do so.

In some cases the mail relay only accepts mails from correctly named
hosts. In this case you may also have to set the containers local host
name using the option `--hostname 'monitoring.mydomain.com'`.

If your mail relay requires you to customize the containers mailer
configuration, you may have to mount a postfix configuration file or
directory into the container.

The container is using postfix as local MTA which takes care about
spooling in case the mail relay is currently not reachable.

[[enabling-livestatus-via-tcp]]
Enabling Livestatus via TCP
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you plan to use your site in a distributed setup or want to access
Livestatus via network for some other reason you can enable it during
container creation by adding `-e CMK_LIVESTATUS_TCP=on -p 6557:6557` to
the create or run command. It will configure the site to open the TCP
port 6557 and tell the host to share the containers port 6557 with the
network.

[[event-console]]
Event Console
~~~~~~~~~~~~~

The Event Console is enabled by default in the container. In case you
want it to listen for incoming syslog messages or SNMP traps on the
network you will first have to make the Event Console open the network
ports using `omd config`. The you have to forward the hosts port to the
container. Use `-p 162:162/udp` to forward SNMP traps, `-p 514:514/udp`
for syslog UDP and `-p 514:514/tcp` for syslog TCP.

[[interactive-shell-access]]
Interactive shell access
~~~~~~~~~~~~~~~~~~~~~~~~

Most administrative tasks are done as site user. To get a shell execute
this on the docker node:

....
docker container exec -it -u cmk monitoring bash
....

In case you need a root shell remove the `-u cmk` argument from the
command above.

[[updating-check_mk]]
Updating Check_MK
~~~~~~~~~~~~~~~~~

Updating Check_MK in a container is not as straight forward as you might
expect. The main problem is that the sites configuration and local data
need to be updated to the target version while the original version is
still available. This is normally done by using the `omd update`
command.

The procedure works like this:

1.  Create a backup of the current state
2.  Perform the site update using an intermediate container
3.  Replace the old container with a new one

Now let's go through this process in detail:

[[our-starting-point]]
1. Our starting point
^^^^^^^^^^^^^^^^^^^^^

Assume you have a container running named container. It uses an Check_MK
Enterprise Edition container with version 1.5.0p2. It may have been
created using this command:

....
docker container run -dit -p 8080:5000 --tmpfs /omd/sites/cmk/tmp -v /omd/sites --name monitoring -v /etc/localtime:/etc/localtime checkmk/check-mk-enterprise:1.5.0p2
....

Now you want to update the instance to 1.5.0p3.

[[stop-your-current-container]]
2. Stop your current container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before performing the backup stop the current container. If you want to
have less downtime, you may try another approach. We do it like this for
consistency and simplicity.

....
docker stop monitoring
....

[[backup-your-current-state]]
2. Backup your current state
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The goal of the update procedure is to update the sites data. As you may
know it is stored on a dedicated docker volume (in case you created the
container with `-v /omd/sites`). This instructs docker to store all data
below this path in a storage area which is independent of the single
container on the node.

For the backup this means it is not enough to backup or snapshot the
container. We need to take a backup of the data volume. This can be done
like this:

....
docker cp monitoring:/omd/sites - > /path/to/backup.tar
....

You may have a better backup solution. Use it!

[[update-the-site-using-an-intermediate-container]]
3. Update the site using an intermediate container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We create the intermediate container to perform the update. It is the
place where we make both, the old and the new version available and
execute `omd update`. The container is created using the new container
version. The container is removed automatically when shutting it down.

....
docker container run -it --rm --volumes-from monitoring --name monitoring_update checkmk/check-mk-enterprise:1.5.0p3 bash
....

Now add the origin version to the intermediate container.

....
docker cp -L monitoring:/omd/versions/default - | docker cp - monitoring_update:/omd/versions
....

Until now no modification has been made. You could stop the intermediate
container and start the old container again. But now we perform the
`omd update` which will change the sites version.

....
docker exec -it -u cmk monitoring_update omd update
....

Once you have finished this step you can stop the intermediate container
`monitoring_update` by terminating the open shell.

[[replace-the-old-container-with-a-new-one]]
4. Replace the old container with a new one
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Move the old container out of the way for the new one:

....
docker rename monitoring monitoring_old
....

Now create a new container using the previously updated volume.

....
docker container run -dit -p 8080:5000 --tmpfs /omd/sites/cmk/tmp --volumes-from monitoring_old --name monitoring checkmk/check-mk-enterprise:1.5.0p3
....

Have a look at the container logs. It should've been started without
issue:

....
docker container logs monitoring
....

[[cleanup]]
5. Cleanup
^^^^^^^^^^

If everything went fine you can now finalize your update by cleaning up
the old container

....
docker rm monitoring_old
....

[[building-your-own-container]]
Building your own container
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Besides the prebuilt containers, which are available through Docker Hub,
you may also create your own container images.

1.  Check out the current Check_MK git
2.  Navigate to the `docker` directory
3.  Imagine you want to build an 1.5.0p3 Enterprise Edition container
image. Do it like this:

....
docker build \
    --build-arg CMK_VERSION=1.5.0p3 \
    --build-arg CMK_EDITION=enterprise \
    --build-arg CMK_DL_CREDENTIALS='myusername:secretpassword' \
    -t mycompany/check-mk-enterprise:1.5.0p3
....

Doing it like this the build process will download 2 files from our download
server: The Debian stretch package and the GPG public key for verifying the
package signature. To prevent this you may put the files that are needed during
the build into the `docker` directory. For the above call you would have to put
the `check-mk-enterprise-1.5.0p3.stretch_amd64.deb` and `Check_MK-pubkey.gpg`
into this directory.

We'll offer prebuilt images for the Enterprise and Managed Services
Edition in the future. For the moment you'll have to build them on your
own (e.g. using the command above).
