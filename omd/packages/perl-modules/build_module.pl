#!/usr/bin/env perl
use warnings;
use strict;
use Config;
use BuildHelper;

my $verbose = 0;
my $PERL    = "/usr/bin/perl";
my $TARGET  = "/tmp/thruk_p5_dist";
my $DISTRO  = "";
if($ARGV[0] =~ m/perl$/) {
    $PERL = $ARGV[0]; shift @ARGV;
}
if($ARGV[0] eq '-v') {
    $verbose = 1; shift @ARGV;
}
if($ARGV[0] eq '-d') {
    shift @ARGV;
    $DISTRO = shift @ARGV;
}
if($ARGV[0] eq '-p') {
    shift @ARGV;
    $TARGET = shift @ARGV;
}

if(!defined $ENV{'PERL5LIB'} or $ENV{'PERL5LIB'} eq "") {
    print "dont call $0 directly, use the 'make'\n";
    exit 1;
}

my $x = 1;
my $max = scalar @ARGV;
for my $mod (@ARGV) {
    BuildHelper::install_module($mod, $TARGET, $PERL, $verbose, $x, $max, $ENV{'FORCE'}) || exit 1;
    $x++;
}
exit;
