package Monitoring::Livestatus::UNIX;

use 5.000000;
use strict;
use warnings;
use IO::Socket::UNIX;
use Carp;
use base "Monitoring::Livestatus";

=head1 NAME

Monitoring::Livestatus::UNIX - connector with unix sockets

=head1 SYNOPSIS

    use Monitoring::Livestatus;
    my $nl = Monitoring::Livestatus::UNIX->new( '/var/lib/livestatus/livestatus.sock' );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Monitoring::Livestatus::UNIX> object. C<new> takes at least the socketpath.
Arguments are the same as in C<Monitoring::Livestatus>.
If the constructor is only passed a single argument, it is assumed to
be a the C<socket> specification. Use either socker OR server.

=cut

sub new {
    my $class = shift;
    unshift(@_, "peer") if scalar @_ == 1;
    my(%options) = @_;
    $options{'name'} = $options{'peer'} unless defined $options{'name'};

    $options{'backend'} = $class;
    my $self = Monitoring::Livestatus->new(%options);
    bless $self, $class;
    confess('not a scalar') if ref $self->{'peer'} ne '';

    return $self;
}


########################################

=head1 METHODS

=cut

sub _open {
    my $self      = shift;

    if(!-S $self->{'peer'}) {
        my $msg = "failed to open socket $self->{'peer'}: $!";
        if($self->{'errors_are_fatal'}) {
            croak($msg);
        }
        $Monitoring::Livestatus::ErrorCode    = 500;
        $Monitoring::Livestatus::ErrorMessage = $msg;
        return;
    }
    my $sock = IO::Socket::UNIX->new(
                                        Peer     => $self->{'peer'},
                                        Type     => SOCK_STREAM,
                                     );
    if(!defined $sock or !$sock->connected()) {
        my $msg = "failed to connect to $self->{'peer'} :$!";
        if($self->{'errors_are_fatal'}) {
            croak($msg);
        }
        $Monitoring::Livestatus::ErrorCode    = 500;
        $Monitoring::Livestatus::ErrorMessage = $msg;
        return;
    }

    if(defined $self->{'query_timeout'}) {
        # set timeout
        $sock->timeout($self->{'query_timeout'});
    }

    return($sock);
}


########################################

sub _close {
    my $self = shift;
    my $sock = shift;
    return unless defined $sock;
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
