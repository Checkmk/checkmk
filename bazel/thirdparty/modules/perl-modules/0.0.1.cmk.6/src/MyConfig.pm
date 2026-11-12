# this config will be only read once before
# the first call of cpan
$CPAN::Config = {
  'cpan_home'                     => glob('~/.cpan'),
  'urllist'                       => [  q[ftp://cpan.cpantesters.org/CPAN/],
                                        q[ftp://cpan.mirror.iphh.net/pub/CPAN/],
                                        q[ftp://cpan.noris.de/pub/CPAN/],
                                        q[ftp://ftp-stud.hs-esslingen.de/pub/Mirrors/CPAN/],
                                        q[ftp://ftp.cw.net/pub/CPAN/]
                                     ],
  'auto_commit'                   => q[1],
  'prerequisites_policy'          => q[follow],
  'build_requires_install_policy' => q[yes],
  'connect_to_internet_ok'        => q[yes],
};
1;
__END__
