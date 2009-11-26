#!/usr/bin/env perl
#
# $Id$
#
use strict;
use warnings;
use File::Spec;
use Test::More;
use English qw(-no_match_vars);

if ( not $ENV{TEST_AUTHOR} ) {
    my $msg = 'Author test.  Set $ENV{TEST_AUTHOR} to a true value to run.';
    plan( skip_all => $msg );
}

eval { require Test::Pod::Coverage; };

if ( $EVAL_ERROR ) {
   my $msg = 'Test::Pod::Coverage required to criticise pod';
   plan( skip_all => $msg );
}

eval "use Test::Pod::Coverage 1.00";
all_pod_coverage_ok();
