REDIS := redis
REDIS_VERS := 6.2.6
REDIS_DIR := $(REDIS)-$(REDIS_VERS)

REDIS_BUILD := $(BUILD_HELPER_DIR)/$(REDIS_DIR)-build
REDIS_INSTALL := $(BUILD_HELPER_DIR)/$(REDIS_DIR)-install

$(REDIS_BUILD):
	bazel build @redis//:build
	$(TOUCH) $@

$(REDIS_INSTALL): $(REDIS_BUILD)
	bazel run @redis//:deploy
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rx,Fo=rx build/by_bazel/redis/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rwx,Fo=rx build/by_bazel/redis/skeleton/ $(DESTDIR)$(OMD_ROOT)/skel
	cd $(DESTDIR)$(OMD_ROOT)/bin/ && \
	$(LN) -sf redis-server redis-check-aof && \
	$(LN) -sf redis-server redis-check-rdb && \
	$(LN) -sf redis-server redis-sentinel
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/
	cd $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/ && \
	$(LN) -sf ../init.d/redis 85-redis
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/redis
	chmod 664 $(DESTDIR)$(OMD_ROOT)/skel/etc/logrotate.d/redis 
	chmod 664 $(DESTDIR)$(OMD_ROOT)/skel/etc/redis/redis.conf 
	$(TOUCH) $@
