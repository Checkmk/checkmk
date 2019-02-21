def test_perl_modules(site):
    # TODO: Complete this list
    test_modules = [
        "Getopt::Long",
        "File::stat",
        "File::Find",
        "File::Path",
        "Net::SNMP",
        "SNMP",
        "Nagios::Plugin",
        "Test::Simple",
        "Try::Tiny",
        "Params::Validate",
        "Module::Runtime",
        "Module::Metadata",
        "Module::Implementation",
        "Module::Build",
        "Math::Calc::Units",
        "Config::Tiny",
        "Class::Accessor",

        # Webinject
        "Carp",
        "LWP",
        "URI",
        "HTTP::Request::Common",
        "HTTP::Cookies",
        "XML::Simple",
        "Time::HiRes",
        "Crypt::SSLeay",
        "XML::Parser",
        "Data::Dumper",
        "File::Temp",

        # Check_oracle_health
        "File::Basename",
        "IO::File",
        "File::Copy",
        "Sys::Hostname",
        "Data::Dumper",
        "Net::Ping",
    ]

    for module in test_modules:
        p = site.execute(["perl", "-e", "use %s" % module])
        assert p.wait() == 0, "Failed to load module: %s" % module
