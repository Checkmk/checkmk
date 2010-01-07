#line 1
package Module::Install::Scripts;

use strict 'vars';
use Module::Install::Base ();

use vars qw{$VERSION @ISA $ISCORE};
BEGIN {
	$VERSION = '0.91';
	@ISA     = 'Module::Install::Base';
	$ISCORE  = 1;
}

sub install_script {
	my $self = shift;
	my $args = $self->makemaker_args;
	my $exe  = $args->{EXE_FILES} ||= [];
        foreach ( @_ ) {
		if ( -f $_ ) {
			push @$exe, $_;
		} elsif ( -d 'script' and -f "script/$_" ) {
			push @$exe, "script/$_";
		} else {
			die("Cannot find script '$_'");
		}
	}
}

1;
