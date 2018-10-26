include ../../Makefile.omd

NAME     := freetds
VERSION  := 0.95.95
DIR      := $(NAME)-$(VERSION)

BUILD-HELPER-DIR := .$(NAME)-build-helper

TARXZ := $(shell which tar) xzf
TOUCH := $(shell which touch)
MKDIR := $(shell which mkdir)

.PHONY: build install skel clean
build: $(BUILD-HELPER-DIR)/build

unpack: $(BUILD-HELPER-DIR)/unpack

$(BUILD-HELPER-DIR)/unpack: $(DIR).tar.gz
	$(MKDIR) $(BUILD-HELPER-DIR)
	$(TARXZ) $<
	$(TOUCH) $@

$(BUILD-HELPER-DIR)/build: $(BUILD-HELPER-DIR)/unpack
	cd $(DIR) && \
	    ./configure \
		--enable-msdblib \
		--prefix=$(OMD_ROOT) \
		--sysconfdir=/etc/freetds \
		--with-tdsver=7.1 \
		--disable-apps \
		--disable-server \
		--disable-pool \
		--disable-odbc
	$(MAKE) -C $(DIR) -j4
# Package python-modules needs some stuff during the build.
	$(MAKE) -C $(DIR)/include prefix=$(PACKAGE_FREETDS_DESTDIR) install
	$(MAKE) -C $(DIR)/src/dblib prefix=$(PACKAGE_FREETDS_DESTDIR) install
	$(TOUCH) $@

install: $(BUILD-HELPER-DIR)/build
# At runtime we need only the libraries.
	$(MAKE) -C $(DIR)/src/dblib DESTDIR=$(DESTDIR) install

skel:

clean:
	$(RM) -r $(DIR) $(BUILD-HELPER-DIR)
