include ../../Makefile.omd

NAME     = perl-modules
VERSION  = $(OMD_VERSION)
DISTRO   = $(shell ../../distro)

MODULES = \
          Capture-Tiny-0.27.tar.gz \
          Carp-Clan-6.04.tar.gz \
          Class-Accessor-0.34.tar.gz \
          Class-Singleton-1.5.tar.gz \
          Config-General-2.56.tar.gz \
          Crypt-Blowfish_PP-1.12.tar.gz \
          Data-Dumper-2.154.tar.gz \
          Digest-MD5-2.54.tar.gz \
          Digest-SHA1-2.13.tar.gz \
	  ExtUtils-Constant-0.23.tar.gz \
          Getopt-Long-2.43.tar.gz \
          HTTP-Date-6.02.tar.gz \
	  Locale-Maketext-Simple-0.21.tar.gz \
          Math-Calc-Units-1.07.tar.gz \
          Module-Find-0.12.tar.gz \
	  Module-Load-0.32.tar.gz \
	  Params-Check-0.38.tar.gz \
	  PathTools-3.47.tar.gz \
          Scalar-List-Utils-1.42.tar.gz \
          Sub-Exporter-Progressive-0.001011.tar.gz \
          Sub-Install-0.928.tar.gz \
          Sys-SigAction-0.21.tar.gz \
          Term-ReadLine-Gnu-1.25.tar.gz \
          Term-ShellUI-0.92.tar.gz \
          Term-Size-0.207.tar.gz \
          TermReadKey-2.37.tar.gz \
          Text-ParseWords-3.29.tar.gz \
          Time-HiRes-1.9726.tar.gz \
          Try-Tiny-0.22.tar.gz \
          Perl-OSType-1.008.tar.gz \
          base-2.18.tar.gz \
          Archive-Zip-1.43.tar.gz \
          HTML-Parser-3.71.tar.gz \
          Term-Clui-1.70.tar.gz \
          URI-1.67.tar.gz \
          Class-MethodMaker-2.22.tar.gz \
          HTTP-Message-6.06.tar.gz \
	  Module-Load-Conditional-0.64.tar.gz \
          Net-HTTP-6.07.tar.gz \
          Term-ProgressBar-2.17.tar.gz \
          Test-Cmd-1.08.tar.gz \
          Test-Simple-1.001014.tar.gz \
          XML-LibXML-2.0117.tar.gz \
	  HTTP-Cookies-6.01.tar.gz \
	  IPC-Cmd-0.92.tar.gz \
          ExtUtils-CBuilder-0.280220.tar.gz \
          ExtUtils-ParseXS-3.24.tar.gz \
          Module-Metadata-1.000027.tar.gz \
	  IO-1.25.tar.gz \
	  LWP-Protocol-https-6.06.tar.gz \
          List-AllUtils-0.09.tar.gz \
          libwww-perl-6.13.tar.gz \
          Module-Build-0.4007.tar.gz \
          Module-Runtime-0.014.tar.gz \
	  YAML-Tiny-1.67.tar.gz \
	  Module-Install-1.16.tar.gz \
          XML-NamespaceSupport-1.11.tar.gz \
          XML-SAX-Base-1.08.tar.gz \
          XML-SAX-0.99.tar.gz \
	  XML-Simple-2.20.tar.gz \
          Monitoring-Livestatus-0.74.tar.gz \
          Params-Util-1.07.tar.gz \
	  Path-Class-0.35.tar.gz \
	  Socket-2.019.tar.gz \
          XML-Parser-2.44.tar.gz \
          XML-Twig-3.48.tar.gz \
          Config-Tiny-2.20.tgz \
          Crypt-SSLeay-0.72.tar.gz \
          File-SearchPath-0.06.tar.gz \
          Module-Implementation-0.09.tar.gz \
          Params-Validate-1.18.tar.gz \
          DateTime-Locale-0.45.tar.gz \
          DateTime-TimeZone-1.88.tar.gz \
          Monitoring-Plugin-0.38.tar.gz \
          Nagios-Plugin-0.36.tar.gz \
          DateTime-1.18.tar.gz

build:
	mkdir -p $(P5TMPDIST)/dest
	mkdir -p $(P5TMPDIST)/src
	rsync -a src/. $(P5TMPDIST)/src/.
	rsync -a build_module.pl lib $(P5TMPDIST)/src/.
	echo "install --install_base $(P5TMPDIST)/dest" > $(P5TMPDIST)/dest/.modulebuildrc
	unset LANG; \
	unset PERL5LIB; \
	unset PERL_MB_OPT; \
	unset PERL_LOCAL_LIB_ROOT; \
	unset PERL_MM_OPT; \
	export PATH=$(P5TMPDIST)/dest/bin:$$PATH; \
	    export PERL_MM_OPT=INSTALL_BASE=$(P5TMPDIST)/dest; \
	    export PERL_MB_OPT=--install_base=$(P5TMPDIST)/dest; \
	    export MODULEBUILDRC=$(P5TMPDIST)/dest/.modulebuildrc; \
	    export PERL5LIB=$(P5TMPDIST)/dest/lib/perl5:$(P5TMPDIST)/src/lib:$(P5TMPDIST)/src/Crypt-SSLeay-0.72; \
	    cd $(P5TMPDIST)/src && \
	        FORCE=1 ./build_module.pl -d "$(DISTRO)" -p $(P5TMPDIST)/dest \
	            ExtUtils-MakeMaker-*.tar.gz \
	            parent-*.tar.gz \
	            version-*.tar.gz \
	            Module-CoreList-*.tar.gz \
	            common-sense-*.tar.gz \
	            Types-Serialiser-*.tar.gz \
	            JSON-*.tar.gz; \
	    export PERL_JSON_BACKEND='JSON::XS'; \
	    cd $(P5TMPDIST)/src && \
	        ./build_module.pl -d "$(DISTRO)" -p $(P5TMPDIST)/dest $(MODULES)
	cd $(P5TMPDIST)/dest/lib/perl5/ && rm -f utils.pm && ln -s ../../../nagios/plugins/utils.pm .
	mkdir -p $(P5TMPDIST)/dest/lib/perl5/CPAN
	cp MyConfig.pm $(P5TMPDIST)/dest/lib/perl5/CPAN/MyConfig.skel

install:
	if [ -z $(DESTDIR) ]; then echo "cannot install without DESTDIR set!"; exit 1; fi
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/perl5 $(DESTDIR)$(OMD_ROOT)/bin
	rsync -a $(P5TMPDIST)/dest/lib $(DESTDIR)$(OMD_ROOT)/lib/perl5/
	rsync -a $(P5TMPDIST)/dest/bin $(DESTDIR)$(OMD_ROOT)/lib/perl5/
	mkdir -p $(DESTDIR)$(OMD_ROOT)/local/lib/perl5
	install -m 755 bin/cpan.wrapper $(DESTDIR)$(OMD_ROOT)/bin/cpan.wrapper

skel:
	echo "install  --install_base  ###ROOT###/local/lib/perl5" > $(SKEL)/.modulebuildrc

clean:
	rm -rf src/inc $(P5TMPDIST)
