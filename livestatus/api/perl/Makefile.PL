use 5.000000;
use ExtUtils::MakeMaker;
# See lib/ExtUtils/MakeMaker.pm for details of how to influence
# the contents of the Makefile that is written.
WriteMakefile(
    NAME           => 'Nagios::MKLivestatus',
    VERSION_FROM   => 'lib/Nagios/MKLivestatus.pm',
    PREREQ_PM      => {
                          'threads'          => 1.07,
                          'IO::Socket::UNIX' => 0,
                          'IO::Socket::INET' => 0,
                      },
    ABSTRACT_FROM  => 'lib/Nagios/MKLivestatus.pm',
    AUTHOR         => 'Sven Nierlein <nierlein@cpan.org>',
    $ExtUtils::MakeMaker::VERSION >= 6.31
    ? ( 'LICENSE' => 'perl' ) : (),
);
