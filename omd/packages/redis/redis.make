REDIS := redis
REDIS_VERS := 6.2.20
REDIS_DIR := $(REDIS)-$(REDIS_VERS)

REDIS_BUILD := $(BUILD_HELPER_DIR)/$(REDIS_DIR)-build
REDIS_INSTALL := $(BUILD_HELPER_DIR)/$(REDIS_DIR)-install

.PHONY: $(REDIS_BUILD)
$(REDIS_BUILD):
	$(BAZEL_BUILD) @redis//:build
	$(BAZEL_BUILD) @redis//:skel

.PHONY: $(REDIS_INSTALL)
$(REDIS_INSTALL): $(REDIS_BUILD)
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rx,Fo=rx $(BAZEL_BIN_EXT)/redis/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rwx,Fo=rx $(BAZEL_BIN_EXT)/redis/skeleton/ $(DESTDIR)$(OMD_ROOT)/skel
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/
	cd $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/ && \
	$(LN) -sf ../init.d/redis 85-redis
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/redis
	chmod 640 $(DESTDIR)$(OMD_ROOT)/skel/etc/logrotate.d/redis
	chmod 750 $(DESTDIR)$(OMD_ROOT)/skel/etc/redis
	chmod 640 $(DESTDIR)$(OMD_ROOT)/skel/etc/redis/redis.conf
	chmod 750 $(DESTDIR)$(OMD_ROOT)/skel/etc/init.d/redis
