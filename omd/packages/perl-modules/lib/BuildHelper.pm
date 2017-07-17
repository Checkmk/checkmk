package BuildHelper;

use warnings;
use strict;
use Config;
use Data::Dumper;
use Storable qw/lock_store lock_retrieve/;
use Cwd;

####################################
# Settings
$Data::Dumper::Sortkeys = 1;
my $verbose = 0;
my $additional_deps = {
  'IO'                 => { 'ExtUtils::ParseXS' => '3.21' },
  'Class::MethodMaker' => { 'Fatal'             => '1' },
};
# override which dependencies should not be considered a core module
my $no_core_dependency = {
  'Fatal' => 1,
};

####################################
# is this a core module?
sub is_core_module {
    my($module, $perl_version) = @_;
    eval {
        require Module::CoreList;
        Module::CoreList->import();
    };
    return if $@;
    my @v = split/\./, $Config{'version'};
    my $v = $perl_version || $v[0] + $v[1]/1000;
    #my $v = "5.020000";
    return if defined $no_core_dependency->{$module};
    if(exists $Module::CoreList::version{$v}{$module}) {
        return($Module::CoreList::version{$v}{$module});
    }
    return;
}

####################################
# execute a command
sub cmd {
    my($cmd,$force) = @_;
    print "[INFO] cmd: $cmd\n" if $verbose;
    my $out = "";
    open(my $ph, '-|', $cmd." 2>&1") or die("cannot execute cmd: $cmd");
    while(my $line = <$ph>) {
        $out .= $line;
    }
    close($ph);
    if($? != 0 and !defined $force) { my $rc = $?>>8; die("cmd failed (rc:$rc): $cmd\n$out") };
    return $out;
}

####################################
# get all dependencies for a tarball
# needs a filename like: Storable-2.21.tar.gz
sub get_deps {
    my($file, $download, $quiet) = @_;
    $quiet = 0 unless defined $quiet;

    our %deps_cache;
    our %deps_files;
    our %already_checked;
    return if defined $already_checked{$file};
    $already_checked{$file} = 1;

    print "checking dependecies for: $file\n" unless $quiet;
    print "." if $quiet == 1;
    my $meta = get_meta_for_tarball($file);

    my $deps = get_deps_from_meta($meta);
    add_additional_deps($file, $deps);
    $deps_cache{$file} = $deps;
    for my $dep (keys %{$deps}) {
        my $depv = $deps->{$dep};
        my $cv   = is_core_module($dep);
        if($cv and version_compare($cv, $depv)) {
            print "   -> $dep ($depv) skipped core dependency\n" unless $quiet;
            next;
        }
        print "   -> $dep ($depv)\n" unless $quiet;
        if($download) {
            download_module($dep, $depv);
        }
    }
    return \%deps_cache;
}

####################################
# download all dependencies for a tarball
# needs a filename like: Storable-2.21.tar.gz
sub download_deps {
    my $file = shift;
    return get_deps($file, 1);
}

####################################
# download a module
# needs a module name like: IO::All
sub download_module {
    my $mod    = shift;
    my $ver    = shift || 0;
    my $no_dep = shift || 0;
    my $quiet  = shift || 0;

    print "[INFO] download_module($mod, $ver)\n" if $verbose;

    our %already_downloaded;
    our %deps_checked;
    our @downloaded;
    return \@downloaded if defined $already_downloaded{$mod.$ver};
    $already_downloaded{$mod.$ver} = 1;

    # we dont need core modules or perl dependency
    if($mod eq 'perl') { return \@downloaded; }

    my $urlpath = get_url_for_module($mod);
    return \@downloaded if defined $already_downloaded{$urlpath};
    if($urlpath =~ m/\/perl\-[\d\.]+\.tar\.gz/) {
        $already_downloaded{$urlpath} = 1;
        print "     -> links to perl\n";
        return \@downloaded;
    }
    my $tarball=$urlpath; $tarball =~ s/^.*\///g;

    if( ! -f $tarball and !defined $already_downloaded{$urlpath}) {
        cmd('wget --retry-connrefused -q "http://search.cpan.org'.$urlpath.'"');
        $already_downloaded{$urlpath} = 1;
        download_deps($tarball) unless $no_dep == 1;
        push @downloaded, $tarball;
        print "downloaded $tarball\n" unless $quiet;
    } else {
        if(!defined $deps_checked{$tarball}) {
            print "$tarball already downloaded\n";
            #print "rechecking dependency\n";
            #download_deps($tarball);
            $deps_checked{$tarball} = 1;
        } else {
            print "$tarball already downloaded\n";
        }
    }
    return \@downloaded;
}

####################################
sub download_src {
    my $module = shift;
    cmd('wget --retry-connrefused -q "http://thruk.org/libs/src/'.$module.'"');
    return;
}

####################################
# download a module
# needs a filename like: Storable-2.21.tar.gz
# returns module name and version
sub file_to_module {
    my $file = shift;
    my($module,$version) = ($file, 0);

    if($file =~ m/\-([0-9\.]*)(\.[\w\d]+)*(\.tar\.gz|\.tgz|\.zip)/) {
        $version = $1;
    }

    $module =~ s/\-[0-9\.\w]*(\.tar\.gz|\.tgz|\.zip)//g;
    $module =~  s/\-/::/g;
    $module = translate_module_name($module);

    return($module,$version);
}

####################################
# return real module name
# TODO: get real name from http://search.cpan.org/search?mode=dist&query=<module>
sub translate_module_name {
    my $name = shift;
    my $tr = {
        'Filter'                => 'Filter::exec',
        'IO::Compress'          => 'IO::Compress::Base',
        'IO::stringy'           => 'IO::Scalar',
        'Scalar::List::Utils'   => 'List::Util::XS',
        'libwww::perl'          => 'LWP',
        'Template::Toolkit'     => 'Template',
        'TermReadKey'           => 'Term::ReadKey',
        'Gearman'               => 'Gearman::Client',
        'PathTools'             => 'File::Spec',
        'libnet'                => 'Net::Cmd',
        'podlators'             => 'Pod::Man',
        'Text::Tabs+Wrap'       => 'Text::Tabs',
    };
    $name =~ s/^inc::Module::Install.*?/Module::Install/g;
    return $tr->{$name} if defined $tr->{$name};
    return $name;
}

####################################
# return filename from list
sub module_to_file {
    my($mod, $files, $version) = @_;
    $version = 0 unless defined $version;
    if($version > 0 and defined $files->{$mod}) {
        my($m,$v) = file_to_module($files->{$mod});
        return $files->{$mod} if version_compare($v, $version);
    }
    return $files->{$mod} if defined $files->{$mod};
    return;
}

####################################
# get dependencies
sub get_all_deps {
    my($quiet) = @_;
    our %deps_cache;
    our %deps_files;
    alarm(60);
    my $data;
    if(-f '.deps.cache') {
        # this may fail due to mismatching hosts systems
        eval {
            $data = lock_retrieve('.deps.cache') or die("cannot read .deps.cache: $!");
        };
        warn($@) if $@;

        # remove all tarballs from cache which no longer exist
        for my $tf (keys %{$data->{'deps'}}) {
            if(!-e 'src/'.$tf) {
                delete $data->{'deps'}->{$tf};
                for my $key (keys %{$data->{'files'}}) {
                    delete $data->{'files'}->{$key} if $data->{'files'}->{$key} eq $tf;
                }
                print " -> cleaned dependecies for: $tf because tarball does not exist anymore\n" unless $quiet;
            }
        }
    }
    alarm(0);
    my $cwd = cwd();
    chdir("src") or die("cannot change to src dir");
    my @tarballs = glob("*.tgz *.tar.gz *.zip");

    %deps_cache = %{$data->{'deps'}}  if defined $data->{'deps'};
    %deps_files = %{$data->{'files'}} if defined $data->{'files'};
    my($x,$max) = (1, scalar @tarballs);
    for my $tarball (sort @tarballs) {
        if(!defined $deps_cache{$tarball}) {
            printf("*** (%3s/%s) ", $x, $max) if($max > 1 and !$quiet);
            get_deps($tarball, undef, $quiet);
        }
        $x++;
    }

    chdir($cwd) or die("cannot change dir back");
    alarm(60);
    lock_store({'files' => \%deps_files, 'deps' => \%deps_cache}, '.deps.cache');
    alarm(0);
    return(\%deps_cache, \%deps_files);
}

####################################
sub sort_by_dependency {
    my $modules = shift;

    my @sorted;

    # ExtUtils-MakeMaker has to go first
    for my $m (sort keys %{$modules}) {
        if($m =~ m/^ExtUtils\-MakeMaker\-\d+/) {
            push @sorted, $m;
            delete $modules->{$m};
        }
    }

    my $num = scalar keys %{$modules};
    while($num > 0) {
        for my $m (sort keys %{$modules}) {
            for my $s (sort keys %{$modules->{$m}}) {
                if(grep {/$s/} @sorted) {
                    delete $modules->{$m}->{$s};
                }
            }
            if(scalar keys %{$modules->{$m}} == 0) {
                push @sorted, $m;
                delete $modules->{$m};
            }
        }
        my $new = scalar keys %{$modules};
        if($new == $num) {
            print Dumper $modules;
            die("circular dependency");
        }
        $num = $new;
    }

    return @sorted;
}

####################################
# compare two version strings
# return 1 if $v1 >= $v2
sub version_compare {
    my($v1,$v2) = @_;
    return 0 if !defined $v1 or $v1 eq 'undef';
    return 1 if !defined $v2 or $v2 eq 'undef';
    $v1 =~ s/^(\d+\.\d+).*$/$1/;
    $v2 =~ s/^(\d+\.\d+).*$/$1/;
    return 1 if $v1 >= $v2;
    return 0;
}

####################################
# sort dependencies
sub sort_deps {
    my $deps  = shift;
    my $files = shift;
    my $already_printed = {};

    # 1st clean up and resolve modules to files
    our $modules = {};
    for my $file (keys %{$deps}) {
        $modules->{$file} = {};
        for my $dep (keys %{$deps->{$file}}) {
            next if $dep eq 'perl';
            next if $dep eq 'strict';
            next if $dep eq 'warnings';
            next if $dep eq 'lib';
            next if $dep eq 'blib';
            next if $dep eq 'utf8';
            next if $dep eq 'v';
            next if $dep eq 'IPC::Open'; # core module but not recognized
            my $cv = is_core_module($dep, 5.008);
            next if $cv;
            my $fdep = module_to_file($dep, $files, $deps->{$file}->{$dep});
            if(defined $fdep) {
                next if $fdep eq $file;
                $modules->{$file}->{$fdep} = 1
            } else {
                if($dep !~ m/^Test::/ and $dep !~ m/^Devel::/) {
                    warn("cannot resolve dependency '$dep' to file, referenced by: $file\n") unless $already_printed->{$dep};
                    $already_printed->{$dep} = 1;
                }
            }
        }
    }

    my @sorted = sort_by_dependency($modules);

    return \@sorted;
}

####################################
# get url for module
sub get_url_for_module {
    my $mod = shift;
    our %url_cache;
    $mod = translate_module_name($mod);
    return $url_cache{$mod} if exists $url_cache{$mod};
    for my $url ('http://search.cpan.org/perldoc?'.$mod, 'http://search.cpan.org/dist/'.$mod) {
        my $out = cmd("wget --retry-connrefused -O - '".$url."'", 1);
        if($out =~ m/href="(\/CPAN\/authors\/id\/.*?\/.*?(\.tar\.gz|\.tgz|\.zip))">/) {
            $url_cache{$mod} = $1;
            return($1);
        }
    }
    print "cannot find $mod on cpan\n";
    exit;
}

####################################
sub install_module {
    my $file    = shift;
    my $TARGET  = shift;
    my $PERL    = shift || '/usr/bin/perl';
    my $verbose = shift || 0;
    my $x       = shift || 1;
    my $max     = shift || 1;
    my $force   = shift;
    die("error: $file does not exist in ".`pwd`) unless -e $file;
    die("error: module name missing") unless defined $file;

    my $LOG = "install.log";
    printf("*** (%3s/%s) ", $x, $max);
    printf("%-55s", $file);

    my($modname, $modvers) = file_to_module($file);

    if( $modname eq "DBD::Oracle") {
        if(defined $ENV{'ORACLE_HOME'} and -f $ENV{'ORACLE_HOME'}."/lib/libclntsh.so") {
            $ENV{'LD_LIBRARY_PATH'} = $ENV{'ORACLE_HOME'}."/lib";
            $ENV{'PATH'}            = $ENV{'PATH'}.":".$ENV{'ORACLE_HOME'}."/bin";
        } else {
            print "skipped\n";
            return 1;
        }
    }

    unless($force) {
        my $core = is_core_module($modname);
        if(version_compare($core, $modvers)) {
            print "skipped core module $core >= $modvers\n";
            return 1;
        }
    }

    my $installed = 0;
    `grep $file $TARGET/modlist.txt 2>&1`;
    $installed = 1 if $? == 0;
    if( $installed and $modname ne 'parent' ) {
        print "already installed\n";
        return 1;
    }

    my $start = time();
    my $dir   = _unpack($file);
    my $cwd   = cwd();
    chdir($dir);
    `rm -f $LOG`;
    print "installing... ";

    my $makefile_opts = '';
    if($modname eq 'XML::LibXML') {
        $makefile_opts = 'FORCE=1';
    }
    if($modname eq 'List::MoreUtils') {
        system("sed -i -e '/url\\s*=>.*github/d' -e '/perl.*=>\\s*\\\$^V/d' Makefile.PL");
    }
    if($modname eq 'GD') {
        system("sed -i 's|-Wformat=0||g' Makefile.PL");
    }

    eval {
        local $SIG{ALRM} = sub { die "timeout on: $file\n" };
        alarm(120); # single module should not take longer than 1 minute
        if( -f "Build.PL" ) {
            `$PERL Build.PL >> $LOG 2>&1 && $PERL ./Build >> $LOG 2>&1 && $PERL ./Build install >> $LOG 2>&1`;
            if($? != 0 ) { die("error: rc $?\n".`cat $LOG`."\n"); }
        } elsif( -f "Makefile.PL" ) {
            `sed -i -e 's/auto_install;//g' Makefile.PL`;
            my $rc;
            # retry because sometimes Makefile.PL will be rebuild due to broken time
            for my $retry (1..3) {
                `echo "\n\n\n" | $PERL Makefile.PL $makefile_opts >> $LOG 2>&1 && make -j 5 >> $LOG 2>&1 && make install >> $LOG 2>&1`;
                $rc = $?;
                last if $rc == 0;
            }
            if($rc != 0 ) { die("error: rc $rc\n".`cat $LOG`."\n"); }
        } else {
            die("error: no Build.PL or Makefile.PL found in $file!\n");
        }
        `grep '^==> Auto-install the' $LOG >/dev/null 2>&1 | grep -v optional`;
        if($? == 0 ) { die("dependency error: rc $?\n".`cat $LOG`."\n"); }
        alarm(0);
    };
    if($@) {
        die("error: $@\n");
    } else {
        `echo $file >> $TARGET/modlist.txt`;
    }

    my $end = time();
    my $duration = $end - $start;
    print "ok (".$duration."s)\n";
    my $grepv = "grep -v 'Test::' | grep -v 'Linux::Inotify2' | grep -v 'IO::KQueue' | grep -v 'prerequisite Carp' | grep -v ExtUtils::Install | grep -v ^Add | grep -v 'We have '";
    system("grep 'Warning: prerequisite' $LOG         | $grepv"); # or die('dependency error');
    system("grep 'is not installed' $LOG | grep ' ! ' | $grepv"); # or die('dependency error');
    system("grep 'is installed, but we need version' $LOG | grep ' ! ' | $grepv"); # or die('dependency error');
    system("grep 'is not a known MakeMaker parameter' $LOG | grep INSTALL_BASE | $grepv") or die('build error');
    chdir($cwd);
    if($duration > 60) {
        chomp(my $pwd = `pwd`);
        print "installation took too long, see $pwd/$dir/$LOG for details\n";
    } else {
        `rm -rf $dir`;
    }

    # makes Module::Build 1000 times faster
    if($modname eq 'JSON::XS') {
        $ENV{'PERL_JSON_BACKEND'} = 'JSON::XS';
    }

    return 1;
}

####################################
# return meta content from unpacked package
sub get_meta_for_dir {
    my($dir) = @_;

    # create Makefile
    my $cwd = cwd();
    chdir($dir);
    alarm(120);
    eval {
        cmd("yes n | perl Makefile.PL", 1) if -e 'Makefile.PL';
        cmd("yes n | perl Build.PL", 1)    if -e 'Build.PL';
    };
    warn($@) if $@;
    alarm(0);
    chdir($cwd);

    my $meta = {};
    if(-s "$dir/MYMETA.json") {
        eval {
            require JSON;
            $meta = JSON::from_json(`cat $dir/MYMETA.json | tr '\n' ' '`);
        };
        print Dumper $@ if $@;
    }
    elsif(-s "$dir/MYMETA.yml") {
        eval {
            $meta = YAML::LoadFile("$dir/META.yml");
        };
        print Dumper $@ if $@;
    }
    elsif(-s "$dir/META.json") {
        eval {
            require JSON;
            $meta = JSON::from_json(`cat $dir/META.json | tr '\n' ' '`);
        };
        print Dumper $@ if $@;
    }
    elsif(-s "$dir/META.yml") {
        eval {
            require YAML;
            $meta = YAML::LoadFile("$dir/META.yml");
        };
        print Dumper $@ if $@;
    }
    $meta->{requires} = {} unless defined $meta->{requires};
    if(-s "$dir/Makefile.PL") {
        my $content = `cat $dir/Makefile.PL`;
        if($content =~ m/WriteMakefile\s*\(/) {
            if($content =~ m/'PREREQ_PM'\s*=>\s*\{(.*?)}/) {
                my $mod_str = $1;
                $mod_str    =~ s/\n/ /g;
                my %modules = $mod_str =~ m/\'(.*?)'\s*=>\s*\'(.*?)\'/;
                %{$meta->{requires}} = (%{$meta->{requires}}, %modules);
            }
        }
        if($content =~ m/^\s*requires\s+/m) {
            my %modules = $content =~ m/^\s*requires\s+(.*?)\s*=>\s*(.*?);/gm;
            %{$meta->{requires}} = (%{$meta->{requires}}, %modules);
        }
        if($content =~ m/^\s*use\s+[a-zA-Z:]+\s*/m) {
            my %modules = $content =~ m/^\s*use\s+([a-zA-Z:]+)\s*([\d\.]+)/gm;
            delete $modules{'inc::Module::Install'};
            delete $modules{'inc::Module::Install::DSL'};
            %{$meta->{requires}} = (%{$meta->{requires}}, %modules);
        }
    }

    # add deps from the Makefile
    if(-s "$dir/Makefile") {
        my $prereq = `grep PREREQ_PM $dir/Makefile`;
        chomp($prereq);
        $prereq =~ s/^#\s+PREREQ_PM\s*=>\s*({.*}).*$/\$req = $1;/g;
        $prereq =~ s/([\w:]+)=/'$1'=/g;
        my $req;
        eval($prereq);
        if(defined $req) {
            for my $mod (keys %{$req}) {
                $meta->{requires}->{$mod} = $req->{$mod};
            }
        }
    }

    $meta->{requires}           = {} unless defined $meta->{requires};
    $meta->{build_requires}     = {} unless defined $meta->{build_requires};
    $meta->{configure_requires} = {} unless defined $meta->{configure_requires};
    $meta->{prereqs}->{'build'}->{'requires'}     = {} unless defined $meta->{prereqs}->{'build'}->{'requires'};
    $meta->{prereqs}->{'configure'}->{'requires'} = {} unless defined $meta->{prereqs}->{'configure'}->{'requires'};
    $meta->{prereqs}->{'runtime'}->{'requires'}   = {} unless defined $meta->{prereqs}->{'runtime'}->{'requires'};

    $meta->{requires}->{'Module::Build'} = 1 if -s $dir.'/Build.PL';

    if(!defined $meta->{name}) {
        $meta->{name} = $dir;
        $meta->{name} =~ s/^(.*)\-.*?$/$1/;
        $meta->{name} =~ s/\-/::/g;
    }

    return $meta;
}

####################################
# return dependencies from meta data
sub get_deps_from_meta {
    my($meta, $all) = @_;
    my %deps = (%{$meta->{requires}},
                %{$meta->{build_requires}},
                %{$meta->{configure_requires}},
                %{$meta->{prereqs}->{'build'}->{'requires'}},
                %{$meta->{prereqs}->{'configure'}->{'requires'}},
                %{$meta->{prereqs}->{'runtime'}->{'requires'}},
               );
    my $stripped_deps = {};
    for my $dep (keys %deps) {
        my $val = $deps{$dep};
        $dep =~ s/('|")//gmx;
        $val =~ s/('|")//gmx;
        next if $val =~ m/win32/;
        next if $dep eq 'perl';
        next if $dep eq 'warnings';
        next if $dep eq 'strict';
        next if $dep eq 'lib';
        next if $dep eq 'v';
        if(!$all) {
            next if $dep eq 'IPC::Open'; # core module but not recognized
            next if $dep =~ m/^Test::/;
            next if $dep eq 'Test';
        }
        $stripped_deps->{$dep} = $val;
    }
    return $stripped_deps;
}

####################################
# add additional dependencies
sub add_additional_deps {
    my($file, $deps) = @_;
    my($modname, $modvers) = file_to_module($file);
    if($additional_deps->{$modname}) {
        for my $key (keys %{$additional_deps->{$modname}}) {
            $deps->{$key} = $additional_deps->{$modname}->{$key};
        }
    }
    return $deps;
}

####################################
# return dependencies from meta data
sub _unpack {
    my $file = shift;
    if($file =~ m/\.zip$/gmx) {
        cmd("unzip $file");
    } else {
        cmd("tar zxf $file");
    }
    my $dir = $file;
    $dir =~  s/(\.tar\.gz|\.tgz|\.zip)//g;
    $dir =~  s/.*\///g;
    $dir =~  s/\-src//g;
    return $dir;
}

####################################
# find orphaned packages
sub get_orphaned {
    my($deps, $files, $verbose) = @_;
    my $orphaned = {};
    for my $file (keys %{$deps}) {
        # verify this module is used somewhere
        my $found = 0;
        for my $file2 (keys %{$deps}) {
            next if $file eq $file2;
            for my $dep2 (keys %{$deps->{$file2}}) {
                next if $dep2 eq 'perl';
                next if $dep2 eq 'strict';
                next if $dep2 eq 'warnings';
                next if $dep2 eq 'lib';
                next if $dep2 eq 'v';
                my $fdep2 = module_to_file($dep2, $files, $deps->{$file2}->{$dep2});
                next unless $fdep2;
                $found = 1 if $fdep2 eq $file;
                if($found && $verbose) { print "$file is used by $file2\n"; }
                last if $found;
            }
            last if $found;
        }
        $orphaned->{$file} = 1 unless $found;
    }
    return $orphaned;
}

####################################
sub get_meta {
    my($in) = @_;
    my $meta = {};
    if($in =~ m/Makefile\.PL$/mx) {
        my $dir = $in;
        $dir    =~ s/Makefile\.PL$//gmx;
        $meta   = get_meta_for_dir($dir);
    }
    elsif($in =~ m/(\.tar.gz|\.tgz|\.zip)$/mx) {
        $meta = get_meta_for_tarball($in);
    }
    else {
        die("unsupported file: ".$in);
    }
    return $meta;
}

####################################
sub get_meta_for_tarball {
    my($file) = @_;

    our %deps_files;

    my $dir  = _unpack($file);
    my $meta = get_meta_for_dir($dir);

    for my $f (split/\n/,`find -name \*.pm; find -name \*.PL`) {
        next if $f =~ m|/inc/|mxo; # skip inc modules included by Module::Install packaged modules
        open(my $fh, '<', $f);
        while(my $line = <$fh>) {
            if($line =~ m/^package\s+(.*?)(\s|;|#)/) {
                $deps_files{$1} = $file;
            }
        }
        if($f =~ m/\.pm$/mx) {
            $f =~ s|^/||gmx;
            $f =~ s|b?lib/||gmx;
            $f =~ s|/|::|gmx;
            $f =~ s|\.pm||gmx;
            $deps_files{$f} = $file;
        }
        close($fh);
    }

    cmd("rm -fr $dir");
    return($meta);
}

1;
