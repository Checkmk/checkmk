package Nagios::MKLivestatus;

use 5.000000;
use strict;
use warnings;
use Data::Dumper;
use Carp;

our $VERSION = '0.22';


=head1 NAME

Nagios::MKLivestatus - access nagios runtime data from check_mk livestatus Nagios addon

=head1 SYNOPSIS

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus->new( socket => '/var/lib/nagios3/rw/livestatus.sock' );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 DESCRIPTION

This module connects via socket to the check_mk livestatus nagios addon. You first have
to install and activate the livestatus addon in your nagios installation.


=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Nagios::MKLivestatus> object. C<new> takes at least the socketpath.
Arguments are in key-value pairs.

    socket                    path to the UNIX socket of check_mk livestatus
    server                    use this server for a TCP connection
    verbose                   verbose mode
    line_seperator            ascii code of the line seperator, defaults to 10, (newline)
    column_seperator          ascii code of the column seperator, defaults to 0 (null byte)
    list_seperator            ascii code of the list seperator, defaults to 44 (comma)
    host_service_seperator    ascii code of the host/service seperator, defaults to 124 (pipe)
    keepalive                 enable keepalive. Default is off
    errors_are_fatal          errors will die with an error message. Default: on
    timeout                   set a general timeout. Used for connect and querys, Default 10sec

If the constructor is only passed a single argument, it is assumed to
be a the C<socket> specification. Use either socker OR server.

=cut

sub new {
    my $class = shift;
    unshift(@_, "socket") if scalar @_ == 1;
    my(%options) = @_;

    my $self = {
                    "verbose"                   => 0,       # enable verbose output
                    "socket"                    => undef,   # use unix sockets
                    "server"                    => undef,   # use tcp connections
                    "line_seperator"            => 10,      # defaults to newline
                    "column_seperator"          => 0,       # defaults to null byte
                    "list_seperator"            => 44,      # defaults to comma
                    "host_service_seperator"    => 124,     # defaults to pipe
                    "keepalive"                 => 0,       # enable keepalive?
                    "errors_are_fatal"          => 1,       # die on errors
                    "backend"                   => undef,   # should be keept undef, used internally
                    "timeout"                   => 10,
               };
    bless $self, $class;

    for my $opt_key (keys %options) {
        if(exists $self->{$opt_key}) {
            $self->{$opt_key} = $options{$opt_key};
        }
        else {
            croak("unknown option: $opt_key");
        }
    }

    if(defined $self->{'socket'} and defined $self->{'server'}) {
        croak('dont use socket and server at once');
    }

    if(!defined $self->{'socket'} and !defined $self->{'server'}) {
        croak('please specify either socket or a server');
    }

    if(!defined $self->{'backend'}) {

        if(defined $self->{'socket'}) {
            use Nagios::MKLivestatus::UNIX;
            $self->{'CONNECTOR'} = new Nagios::MKLivestatus::UNIX(%options);
        }
        elsif(defined $self->{'server'}) {
            use Nagios::MKLivestatus::INET;
            $self->{'CONNECTOR'} = new Nagios::MKLivestatus::INET(%options);
        }
    }

    return $self;
}


########################################

=head1 METHODS

=head2 do

 do($statement)

 Send a single statement without fetching the result.
 Always returns true.

=cut

sub do {
    my $self      = shift;
    my $statement = shift;
    $self->_send($statement);
    return(1);
}


########################################

=head2 selectall_arrayref

 selectall_arrayref($statement)
 selectall_arrayref($statement, %opts)
 selectall_arrayref($statement, %opts, $limit )

 Sends a query and returns an array reference of arrays

    my $arr_refs = $nl->selectall_arrayref("GET hosts");

 to get an array of hash references do something like

    my $hash_refs = $nl->selectall_arrayref("GET hosts", { Slice => {} });

 to get an array of hash references from the first 2 returned rows only

    my $hash_refs = $nl->selectall_arrayref("GET hosts", { Slice => {} }, 2);

 use limit to limit the result to this number of rows

 column aliases can be defined with a rename hash

    my $hash_refs = $nl->selectall_arrayref("GET hosts", { Slice => {}, rename => { 'name' => 'host_name' } });

=cut

sub selectall_arrayref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;
    my $limit     = shift;

    # make opt hash keys lowercase
    %{$opt} = map { lc $_ => $opt->{$_} } keys %{$opt};

    my $result = $self->_send($statement);
    if(!defined $result) {
        return unless $self->{'errors_are_fatal'};
        croak("got undef result for: $statement");
    }

    # trim result set down to excepted row count
    if(defined $limit and $limit >= 1) {
        if(scalar @{$result->{'result'}} > $limit) {
            @{$result->{'result'}} = @{$result->{'result'}}[0..$limit-1];
        }
    }

    if(defined $opt and ref $opt eq 'HASH' and exists $opt->{'slice'}) {
        # make an array of hashes
        my @hash_refs;
        for my $res (@{$result->{'result'}}) {
            my $hash_ref;
            for(my $x=0;$x<scalar @{$res};$x++) {
                my $key = $result->{'keys'}->[$x];
                if(exists $opt->{'rename'} and defined $opt->{'rename'}->{$key}) {
                    $key = $opt->{'rename'}->{$key};
                }
                $hash_ref->{$key} = $res->[$x];
            }
            push @hash_refs, $hash_ref;
        }
        return(\@hash_refs);
    }

    return($result->{'result'});
}


########################################

=head2 selectall_hashref

 selectall_hashref($statement, $key_field)

 Sends a query and returns a hashref with the given key

    my $hashrefs = $nl->selectall_hashref("GET hosts", "name");

=cut

sub selectall_hashref {
    my $self      = shift;
    my $statement = shift;
    my $key_field = shift;

    croak("key is required for selectall_hashref") if !defined $key_field;

    my $result = $self->selectall_arrayref($statement, { Slice => {} });

    my %indexed;
    for my $row (@{$result}) {
        if(!defined $row->{$key_field}) {
            my %possible_keys = keys %{$row};
            croak("key $key_field not found in result set, possible keys are: ".join(', ', sort keys %possible_keys));
        }
        $indexed{$row->{$key_field}} = $row;
    }
    return(\%indexed);
}


########################################

=head2 selectcol_arrayref

 selectcol_arrayref($statement)
 selectcol_arrayref($statement, %opt )

 Sends a query an returns an arrayref for the first columns

    my $array_ref = $nl->selectcol_arrayref("GET hosts\nColumns: name");

    $VAR1 = [
              'localhost',
              'gateway',
            ];

 returns an empty array if nothing was found


 to get a different column use this

    my $array_ref = $nl->selectcol_arrayref("GET hosts\nColumns: name contacts", { Columns => [2] } );

 you can link 2 columns in a hash result set

    my %hash = @{$nl->selectcol_arrayref("GET hosts\nColumns: name contacts", { Columns => [1,2] } )};

    produces a hash with host the contact assosiation

    $VAR1 = {
              'localhost' => 'user1',
              'gateway'   => 'user2'
            };

=cut

sub selectcol_arrayref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    # make opt hash keys lowercase
    %{$opt} = map { lc $_ => $opt->{$_} } keys %{$opt};

    # if now colums are set, use just the first one
    if(!defined $opt->{'columns'} or ref $opt->{'columns'} ne 'ARRAY') {
        @{$opt->{'columns'}} = qw{1};
    }

    my $result = $self->selectall_arrayref($statement);

    my @column;
    for my $row (@{$result}) {
        for my $nr (@{$opt->{'columns'}}) {
            push @column, $row->[$nr-1];
        }
    }
    return(\@column);
}


########################################

=head2 selectrow_array

 selectrow_array($statement)

 Sends a query and returns an array for the first row

    my @array = $nl->selectrow_array("GET hosts");

 returns undef if nothing was found

=cut
sub selectrow_array {
    my $self      = shift;
    my $statement = shift;

    my @result = @{$self->selectall_arrayref($statement, {}, 1)};
    return @{$result[0]} if scalar @result > 0;
    return;
}


########################################

=head2 selectrow_arrayref

 selectrow_arrayref($statement)

 Sends a query and returns an array reference for the first row

    my $arrayref = $nl->selectrow_arrayref("GET hosts");

 returns undef if nothing was found

=cut
sub selectrow_arrayref {
    my $self      = shift;
    my $statement = shift;

    my $result = $self->selectall_arrayref($statement, {}, 1);
    return if !defined $result;
    return $result->[0] if scalar @{$result} > 0;
    return;
}


########################################

=head2 selectrow_hashref

 selectrow_hashref($statement)

 Sends a query and returns a hash reference for the first row

    my $hashref = $nl->selectrow_hashref("GET hosts");

 returns undef if nothing was found

=cut
sub selectrow_hashref {
    my $self      = shift;
    my $statement = shift;

    my $result = $self->selectall_arrayref($statement, { Slice => {} }, 1);
    return if !defined $result;
    return $result->[0] if scalar @{$result} > 0;
    return;
}


########################################

=head2 select_scalar_value

 select_scalar_value($statement)

 Sends a query and returns a single scalar

    my $count = $nl->select_scalar_value("GET hosts\nStats: state = 0");

 returns undef if nothing was found

=cut
sub select_scalar_value {
    my $self      = shift;
    my $statement = shift;

    my $row = $self->selectrow_arrayref($statement);
    return if !defined $row;
    return $row->[0] if scalar @{$row} > 0;
    return;
}

########################################

=head2 errors_are_fatal

 errors_are_fatal($values)

 Enable or disable fatal errors. When enabled the module will croak on any error.

 returns always undef

=cut
sub errors_are_fatal {
    my $self  = shift;
    my $value = shift;

    $self->{'errors_are_fatal'}                = $value;
    $self->{'CONNECTOR'}->{'errors_are_fatal'} = $value;

    return 1;
}


########################################

=head2 verbose

 verbose($values)

 Enable or disable verbose output. When enabled the module will dump out debug output

 returns always true

=cut
sub verbose {
    my $self  = shift;
    my $value = shift;

    $self->{'verbose'}                = $value;
    $self->{'CONNECTOR'}->{'verbose'} = $value;

    return 1;
}



########################################
# INTERNAL SUBS
########################################
sub _send {
    my $self      = shift;
    my $statement = shift;
    my $header = "";

    $Nagios::MKLivestatus::ErrorCode = 0;
    undef $Nagios::MKLivestatus::ErrorMessage;

    return(490, $self->_get_error(490), undef) if !defined $statement;
    chomp($statement);

    my($status,$msg,$body);
    if($statement =~ m/^Separators:/mx) {
        $status = 492;
        $msg    = $self->_get_error($status);
    }

    elsif($statement =~ m/^KeepAlive:/mx) {
        $status = 496;
        $msg    = $self->_get_error($status);
    }

    elsif($statement =~ m/^ResponseHeader:/mx) {
        $status = 495;
        $msg    = $self->_get_error($status);
    }

    elsif($statement =~ m/^ColumnHeaders:/mx) {
        $status = 494;
        $msg    = $self->_get_error($status);
    }

    elsif($statement =~ m/^OuputFormat:/mx) {
        $status = 493;
        $msg    = $self->_get_error($status);
    }

    # should be cought in mlivestatus directly
    elsif($statement =~ m/^Limit:\ (.*)$/mx and $1 !~ m/^\d+$/mx) {
        $status = 403;
        $msg    = $self->_get_error($status);
    }
    elsif($statement =~ m/^GET\ (.*)$/mx and $1 =~ m/^\s*$/mx) {
        $status = 403;
        $msg    = $self->_get_error($status);
    }

    elsif($statement =~ m/^Columns:\ (.*)$/mx and ($1 =~ m/,/mx or $1 =~ /^\s*$/mx)) {
        $status = 405;
        $msg    = $self->_get_error($status);
    }
    elsif($statement !~ m/^GET\ /mx and $statement !~ m/^COMMAND\ /mx) {
        $status = 401;
        $msg    = $self->_get_error($status);
    }

    else {

        # Commands need no additional header
        if($statement !~ m/^COMMAND/mx) {
            $header .= "Separators: $self->{'line_seperator'} $self->{'column_seperator'} $self->{'list_seperator'} $self->{'host_service_seperator'}\n";
            $header .= "ResponseHeader: fixed16\n";
            if($self->{'keepalive'}) {
                $header .= "KeepAlive: on\n";
            }
        }
        my $send = "$statement\n$header";
        print "> ".Dumper($send) if $self->{'verbose'};
        ($status,$msg,$body) = $self->_send_socket($send);
        if($self->{'verbose'}) {
            print "status: ".Dumper($status);
            print "msg:    ".Dumper($msg);
            print "< ".Dumper($body);
        }
    }

    if($status >= 300) {
        $body = '' if !defined $body;
        chomp($body);
        $Nagios::MKLivestatus::ErrorCode    = $status;
        if(defined $body and $body ne '') {
            $Nagios::MKLivestatus::ErrorMessage = $body;
        } else {
            $Nagios::MKLivestatus::ErrorMessage = $msg;
        }
        if($self->{'errors_are_fatal'}) {
            my $nicestatement = $statement;
            $nicestatement    =~ s/\n/\\n/gmx;
            croak("ERROR ".$status." - ".$Nagios::MKLivestatus::ErrorMessage." in query:\n'".$nicestatement."'\n");
        }
        return;
    }

    # return a empty result set if nothing found
    return({ keys => [], result => []}) if !defined $body;

    my $line_seperator = chr($self->{'line_seperator'});
    my $col_seperator  = chr($self->{'column_seperator'});

    my @result;
    ## no critic
    for my $line (split/$line_seperator/m, $body) {
        push @result, [ split/$col_seperator/m, $line ];
    }
    ## use critic

    # for querys with column header, no seperate columns will be returned
    my $keys;
    if($statement =~ m/^Columns:\ (.*)$/mx) {
        my @keys = split/\s+/mx, $1;
        $keys = \@keys;
    } elsif($statement =~ m/^Stats:\ (.*)$/mx) {
        @{$keys} = ($statement =~ m/^Stats:\ (.*)$/gmx);
    } else {
        $keys = shift @result;
    }

    return({ keys => $keys, result => \@result});
}

########################################
sub _open {
    my $self      = shift;
    my $statement = shift;

    # return the current socket in keep alive mode
    if($self->{'keepalive'} and defined $self->{'sock'} and $self->{'sock'}->connected()) {
        return($self->{'sock'});
    }

    my $sock = $self->{'CONNECTOR'}->_open();

    # store socket for later retrieval
    if($self->{'keepalive'}) {
        $self->{'sock'} = $sock;
    }

    return($sock);
}

########################################
sub _close {
    my $self  = shift;
    my $sock  = shift;
    return($self->{'CONNECTOR'}->_close($sock));
}

########################################
sub _send_socket {
    my $self      = shift;
    my $statement = shift;
    my($recv,$header);

    my $sock = $self->_open() or return(491, $self->_get_error(491), $!);
    print $sock $statement;
    if($self->{'keepalive'}) {
        print $sock "\n";
    }else {
        $sock->shutdown(1) or croak("shutdown failed: $!");
    }

    # COMMAND statements never return something
    if($statement =~ m/^COMMAND/mx) {
        $self->_close($sock);
        return('201', $self->_get_error(201), undef);
    }

    $sock->read($header, 16) or return($self->_socket_error($statement, $sock, 'reading header from socket failed'));
    print "header: $header" if $self->{'verbose'};
    my($status, $msg, $content_length) = $self->_parse_header($header);
    return($status, $msg, undef) if !defined $content_length;
    if($content_length > 0) {
        $sock->read($recv, $content_length) or return($self->_socket_error($statement, $sock, 'reading body from socket failed'));
    }

    $self->_close($sock) unless $self->{'keepalive'};
    return($status, $msg, $recv);
}

########################################
sub _socket_error {
    my $self      = shift;
    my $statement = shift;
    my $sock      = shift;
    my $body      = shift;

    my $message = "\n";
    $message   .= "statement           ".Dumper($statement);
    $message   .= "socket->sockname()  ".Dumper($sock->sockname());
    $message   .= "socket->connected() ".Dumper($sock->connected());
    $message   .= "socket->error()     ".Dumper($sock->error());
    $message   .= "message             ".Dumper($body);
    if($self->{'errors_are_fatal'}) {
        confess($message);
    } else {
        carp($message);
    }
    return(500, $self->_get_error(500), $message);
}

########################################
sub _parse_header {
    my $self   = shift;
    my $header = shift;

    if(!defined $header) {
        return(497, $self->_get_error(497), undef);
    }

    my $headerlength = length($header);
    if($headerlength != 16) {
        return(498, $self->_get_error(498), undef);
    }
    chomp($header);

    my $status         = substr($header,0,3);
    my $content_length = substr($header,5);
    if($content_length !~ m/^\s*(\d+)$/mx) {
        return(499, $self->_get_error(499), undef);
    } else {
        $content_length = $1;
    }

    return($status, $self->_get_error($status), $content_length);
}

########################################

=head1 ERROR HANDLING

Errorhandling can be done like this:

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus->new( socket => '/var/lib/nagios3/rw/livestatus.sock' );
    $nl->errors_are_fatal(0);
    my $hosts = $nl->selectall_arrayref("GET hosts");
    if($Nagios::MKLivestatus::ErrorCode) {
        croak($Nagios::MKLivestatus::ErrorMessage);
    }

=cut
sub _get_error {
    my $self = shift;
    my $code = shift;

    my $codes = {
        '200' => 'OK. Reponse contains the queried data.',
        '201' => 'COMMANDs never return something',
        '401' => 'The request contains an invalid header.',
        '402' => 'The request is completely invalid.',
        '403' => 'The request is incomplete.',
        '404' => 'The target of the GET has not been found (e.g. the table).',
        '405' => 'A non-existing column was being referred to',
        '490' => 'no query',
        '491' => 'failed to connect',
        '492' => 'Separators not allowed in statement. Please use the seperator options in new()',
        '493' => 'OuputFormat not allowed in statement. Header will be set automatically',
        '494' => 'ColumnHeaders not allowed in statement. Header will be set automatically',
        '495' => 'ResponseHeader not allowed in statement. Header will be set automatically',
        '496' => 'Keepalive not allowed in statement. Please use the keepalive option in new()',
        '497' => 'got no header',
        '498' => 'header is not exactly 16byte long',
        '499' => 'failed to get content-length from header',
        '500' => 'socket error',
    };

    confess('non existant error code: '.$code) if !defined $codes->{$code};

    return($codes->{$code});
}

1;

=head1 SEE ALSO

For more information about the query syntax and the livestatus plugin installation
see the Livestatus page: http://mathias-kettner.de/checkmk_livestatus.html

=head1 AUTHOR

Sven Nierlein, E<lt>nierlein@cpan.orgE<gt>

=head1 COPYRIGHT AND LICENSE

Copyright (C) 2009 by Sven Nierlein

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut

__END__
