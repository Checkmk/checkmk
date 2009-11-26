package Nagios::MKLivestatus::INET;

use 5.000000;
use strict;
use warnings;
use IO::Socket::INET;
use Carp;
use base "Nagios::MKLivestatus";

=head1 NAME

Nagios::MKLivestatus::INET - connector with tcp sockets

=head1 SYNOPSIS

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus::INET->new( 'localhost:9999' );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Nagios::MKLivestatus::INET> object. C<new> takes at least the server.
Arguments are the same as in C<Nagios::MKLivestatus>.
If the constructor is only passed a single argument, it is assumed to
be a the C<server> specification. Use either socker OR server.

=cut

sub new {
    my $class = shift;
    unshift(@_, "server") if scalar @_ == 1;
    my(%options) = @_;

    $options{'backend'} = $class;
    my $self = Nagios::MKLivestatus->new(%options);
    bless $self, $class;
    return $self;
}


########################################

=head1 METHODS

=cut

sub _open {
    my $self = shift;
    my $sock = IO::Socket::INET->new(
                                     PeerAddr => $self->{'server'},
                                     timeout  => $self->{'timeout'},
                                     );
    if(!defined $sock or !$sock->connected()) {
        my $msg = "failed to connect to $self->{'server'} :$!";
        if($self->{'errors_are_fatal'}) {
            croak($msg);
        }
        $Nagios::MKLivestatus::ErrorCode    = 500;
        $Nagios::MKLivestatus::ErrorMessage = $msg;
        return;
    }
    return($sock);
}


########################################

sub _close {
    my $self = shift;
    my $sock = shift;
    return close($sock);
}


1;

=head1 AUTHOR

Sven Nierlein, E<lt>nierlein@cpan.orgE<gt>

=head1 COPYRIGHT AND LICENSE

Copyright (C) 2009 by Sven Nierlein

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut

__END__
