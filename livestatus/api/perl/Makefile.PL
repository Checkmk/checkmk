# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# IMPORTANT: if you delete this file your app will not work as
# expected.  you have been warned
use inc::Module::Install;

name         'Monitoring-Livestatus';
all_from     'lib/Monitoring/Livestatus.pm';
perl_version '5.006';
license      'perl';

resources(
    'homepage',   => 'http://search.cpan.org/dist/Monitoring-Livestatus/',
    'bugtracker'  => 'http://github.com/sni/Monitoring-Livestatus/issues',
    'repository', => 'http://github.com/sni/Monitoring-Livestatus',
);


requires 'IO::Socket::UNIX';
requires 'IO::Socket::INET';
requires 'Digest::MD5';
requires 'Scalar::Util';
requires 'Test::More'        => '0.87';
requires 'Thread::Queue'     => '2.11';
requires 'utf8';
requires 'Encode';
requires 'JSON::XS';

# test requirements
# these requirements still make it into the META.yml, so they are commented so far
#feature     ('authortests',
#  -default                                                                  => 0,
#  'File::Copy::Recursive'                                                   => 0,
#  'Test::Pod'                                                               => 1.14,
#  'Test::Perl::Critic'                                                      => 0,
#  'Test::Pod::Coverage'                                                     => 0,
#  'Perl::Critic::Policy::Dynamic::NoIndirect'                               => 0,
#  'Perl::Critic::Policy::NamingConventions::ProhibitMixedCaseSubs'          => 0,
#  'Perl::Critic::Policy::ValuesAndExpressions::ProhibitAccessOfPrivateData' => 0,
#);

auto_install;
WriteAll;
