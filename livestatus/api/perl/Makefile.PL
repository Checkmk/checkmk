# IMPORTANT: if you delete this file your app will not work as
# expected.  you have been warned
use inc::Module::Install;

name         'Nagios-MKLivestatus';
all_from     'lib/Nagios/MKLivestatus.pm';
perl_version '5.006';
license      'perl';

requires 'IO::Socket::UNIX';
requires 'IO::Socket::INET';
requires 'Digest::MD5';
requires 'threads'           => '1.07';
requires 'Thread::Queue'     => '2.11';

test_requires 'File::Copy::Recursive';
test_requires 'Test::Pod' => 1.14;
test_requires 'Test::Perl::Critic';
test_requires 'Test::Pod::Coverage';
test_requires 'Perl::Critic::Policy::Dynamic::NoIndirect';
test_requires 'Perl::Critic::Policy::NamingConventions::ProhibitMixedCaseSubs';
test_requires 'Perl::Critic::Policy::ValuesAndExpressions::ProhibitAccessOfPrivateData';

auto_install;
WriteAll;
