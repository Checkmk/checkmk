package Nagios::MKLivestatus;

use 5.006;
use strict;
use warnings;
use Data::Dumper;
use Carp;
use Digest::MD5 qw(md5_hex);
use Nagios::MKLivestatus::INET;
use Nagios::MKLivestatus::UNIX;
use Nagios::MKLivestatus::MULTI;

our $VERSION = '0.28';


=head1 NAME

Nagios::MKLivestatus - access nagios runtime data from check_mk livestatus
Nagios addon

=head1 SYNOPSIS

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus->new(
      socket => '/var/lib/nagios3/rw/livestatus.sock'
    );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 DESCRIPTION

This module connects via socket to the check_mk livestatus nagios addon. You
first have to install and activate the livestatus addon in your nagios
installation.

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Nagios::MKLivestatus> object. C<new> takes at least the
socketpath.  Arguments are in key-value pairs.
See L<EXAMPLES> for more complex variants.

=over 4

=item socket

path to the UNIX socket of check_mk livestatus

=item server

use this server for a TCP connection

=item peer

alternative way to set socket or server, if value contains ':' server is used,
else socket

=item name

human readable name for this connection, defaults to the the socket/server
address

=item verbose

verbose mode

=item line_seperator

ascii code of the line seperator, defaults to 10, (newline)

=item column_seperator

ascii code of the column seperator, defaults to 0 (null byte)

=item list_seperator

ascii code of the list seperator, defaults to 44 (comma)

=item host_service_seperator

ascii code of the host/service seperator, defaults to 124 (pipe)

=item keepalive

enable keepalive. Default is off

=item errors_are_fatal

errors will die with an error message. Default: on

=item warnings

show warnings
currently only querys without Columns: Header will result in a warning

=item timeout

set a general timeout. Used for connect and querys, Default 10sec

=item use_threads

only used with multiple backend connections.
Default is to use threads where available.

=back

If the constructor is only passed a single argument, it is assumed to
be a the C<peer> specification. Use either socker OR server.

=cut

sub new {
    my $class = shift;
    unshift(@_, "peer") if scalar @_ == 1;
    my(%options) = @_;

    my $self = {
      "verbose"                   => 0,       # enable verbose output
      "socket"                    => undef,   # use unix sockets
      "server"                    => undef,   # use tcp connections
      "peer"                      => undef,   # use for socket / server connections
      "name"                      => undef,   # human readable name
      "line_seperator"            => 10,      # defaults to newline
      "column_seperator"          => 0,       # defaults to null byte
      "list_seperator"            => 44,      # defaults to comma
      "host_service_seperator"    => 124,     # defaults to pipe
      "keepalive"                 => 0,       # enable keepalive?
      "errors_are_fatal"          => 1,       # die on errors
      "backend"                   => undef,   # should be keept undef, used internally
      "timeout"                   => 10,      # timeout for tcp connections
      "use_threads"               => undef,   # use threads, default is to use threads where available
      "warnings"                  => 1,       # show warnings, for example on querys without Column: Header
      "logger"                    => undef,   # logger object used for statistical informations and errors / warnings
    };

    for my $opt_key (keys %options) {
        if(exists $self->{$opt_key}) {
            $self->{$opt_key} = $options{$opt_key};
        }
        else {
            croak("unknown option: $opt_key");
        }
    }

    bless $self, $class;

    # set our peer(s) from the options
    my $peers = $self->_get_peers();

    if(!defined $peers) {
        croak('please specify at least one peer, socket or server');
    }

    if(!defined $self->{'backend'}) {
        if(scalar @{$peers} == 1) {
            my $peer = $peers->[0];
            $options{'name'} = $peer->{'name'};
            $options{'peer'} = $peer->{'peer'};
            if($peer->{'type'} eq 'UNIX') {
                $self->{'CONNECTOR'} = new Nagios::MKLivestatus::UNIX(%options);
            }
            elsif($peer->{'type'} eq 'INET') {
                $self->{'CONNECTOR'} = new Nagios::MKLivestatus::INET(%options);
            }
            $self->{'peer'} = $peer->{'peer'};
        }
        else {
            $options{'peer'} = $peers;
            return new Nagios::MKLivestatus::MULTI(%options);
        }
    }

    # set names and peer for non multi backends
    if(defined $self->{'CONNECTOR'}->{'name'} and !defined $self->{'name'}) {
        $self->{'name'} = $self->{'CONNECTOR'}->{'name'};
    }
    if(defined $self->{'CONNECTOR'}->{'peer'} and !defined $self->{'peer'}) {
        $self->{'peer'} = $self->{'CONNECTOR'}->{'peer'};
    }

    $self->{'logger'}->debug('initialized Nagios::MKLivestatus ('.$self->peer_name.')') if defined $self->{'logger'};

    return $self;
}


########################################

=head1 METHODS

=head2 do

 do($statement)
 do($statement, %opts)

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

    my $hash_refs = $nl->selectall_arrayref(
      "GET hosts", { Slice => {} }
    );

to get an array of hash references from the first 2 returned rows only

    my $hash_refs = $nl->selectall_arrayref(
      "GET hosts", { Slice => {} }, 2
    );

use limit to limit the result to this number of rows

column aliases can be defined with a rename hash

    my $hash_refs = $nl->selectall_arrayref(
      "GET hosts", {
        Slice => {},
        rename => {
          'name' => 'host_name'
        }
      }
    );

=cut

sub selectall_arrayref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;
    my $limit     = shift || 0;
    my $result;

    # make opt hash keys lowercase
    %{$opt} = map { lc $_ => $opt->{$_} } keys %{$opt};

    if(defined $self->{'logger'}) {
        my $d = Data::Dumper->new([$opt]);
        $d->Indent(0);
        my $optstring = $d->Dump;
        $optstring =~ s/^\$VAR1\s+=\s+//mx;
        $optstring =~ s/;$//mx;
        my $cleanstatement = $statement;
        $cleanstatement =~ s/\n/\\n/gmx;
        $self->{'logger'}->debug('selectall_arrayref("'.$cleanstatement.'", '.$optstring.', '.$limit.')')
    }

    if(defined $opt->{'addpeer'} and $opt->{'addpeer'}) {
        $result = $self->_send($statement, 1);
    } else {
        $result = $self->_send($statement);
    }

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

    if($opt->{'slice'}) {
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
 selectall_hashref($statement, $key_field, %opts)

Sends a query and returns a hashref with the given key

    my $hashrefs = $nl->selectall_hashref("GET hosts", "name");

=cut

sub selectall_hashref {
    my $self      = shift;
    my $statement = shift;
    my $key_field = shift;
    my $opt       = shift;

    $opt->{'Slice'} = 1 unless defined $opt->{'Slice'};

    croak("key is required for selectall_hashref") if !defined $key_field;

    my $result = $self->selectall_arrayref($statement, $opt);

    my %indexed;
    for my $row (@{$result}) {
        if($key_field eq '$peername') {
            $indexed{$self->peer_name} = $row;
        }
        elsif(!defined $row->{$key_field}) {
            my %possible_keys = keys %{$row};
            croak("key $key_field not found in result set, possible keys are: ".join(', ', sort keys %possible_keys));
        } else {
            $indexed{$row->{$key_field}} = $row;
        }
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

    my $array_ref = $nl->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Columns => [2] }
    );

 you can link 2 columns in a hash result set

    my %hash = @{
      $nl->selectcol_arrayref(
        "GET hosts\nColumns: name contacts",
        { Columns => [1,2] }
      )
    };

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
 selectrow_array($statement, %opts)

Sends a query and returns an array for the first row

    my @array = $nl->selectrow_array("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_array {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;
    $opt          = {} unless defined $opt;

    my @result = @{$self->selectall_arrayref($statement, $opt, 1)};
    return @{$result[0]} if scalar @result > 0;
    return;
}


########################################

=head2 selectrow_arrayref

 selectrow_arrayref($statement)
 selectrow_arrayref($statement, %opts)

Sends a query and returns an array reference for the first row

    my $arrayref = $nl->selectrow_arrayref("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_arrayref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;
    $opt          = {} unless defined $opt;

    my $result = $self->selectall_arrayref($statement, $opt, 1);
    return if !defined $result;
    return $result->[0] if scalar @{$result} > 0;
    return;
}


########################################

=head2 selectrow_hashref

 selectrow_hashref($statement)
 selectrow_hashref($statement, %opt)

Sends a query and returns a hash reference for the first row

    my $hashref = $nl->selectrow_hashref("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_hashref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    $opt->{'Slice'} = 1 unless defined $opt->{'Slice'};

    my $result = $self->selectall_arrayref($statement, $opt, 1);
    return if !defined $result;
    return $result->[0] if scalar @{$result} > 0;
    return;
}


########################################

=head2 select_scalar_value

 select_scalar_value($statement)
 select_scalar_value($statement, %opt)

Sends a query and returns a single scalar

    my $count = $nl->select_scalar_value("GET hosts\nStats: state = 0");

returns undef if nothing was found

=cut
sub select_scalar_value {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    my $row = $self->selectrow_arrayref($statement);
    return if !defined $row;
    return $row->[0] if scalar @{$row} > 0;
    return;
}

########################################

=head2 errors_are_fatal

 errors_are_fatal()
 errors_are_fatal($value)

Enable or disable fatal errors. When enabled the module will croak on any error.

returns the current setting if called without new value

=cut
sub errors_are_fatal {
    my $self  = shift;
    my $value = shift;
    my $old   = $self->{'errors_are_fatal'};

    $self->{'errors_are_fatal'}                = $value;
    $self->{'CONNECTOR'}->{'errors_are_fatal'} = $value if defined $self->{'CONNECTOR'};

    return $old;
}

########################################

=head2 warnings

 warnings()
 warnings($value)

Enable or disable warnings. When enabled the module will carp on warnings.

returns the current setting if called without new value

=cut
sub warnings {
    my $self  = shift;
    my $value = shift;
    my $old   = $self->{'warnings'};

    $self->{'warnings'}                = $value;
    $self->{'CONNECTOR'}->{'warnings'} = $value if defined $self->{'CONNECTOR'};

    return $old;
}



########################################

=head2 verbose

 verbose()
 verbose($values)

Enable or disable verbose output. When enabled the module will dump out debug output

returns the current setting if called without new value

=cut
sub verbose {
    my $self  = shift;
    my $value = shift;
    my $old   = $self->{'verbose'};

    $self->{'verbose'}                = $value;
    $self->{'CONNECTOR'}->{'verbose'} = $value if defined $self->{'CONNECTOR'};

    return $old;
}


########################################

=head2 peer_addr

 $nl->peer_addr()

returns the current peer address

when using multiple backends, a list of all addresses is returned in list context

=cut
sub peer_addr {
    my $self  = shift;

    return "".$self->{'peer'};
}


########################################

=head2 peer_name

 $nl->peer_name()
 $nl->peer_name($string)

if new value is set, name is set to this value

always returns the current peer name

when using multiple backends, a list of all names is returned in list context

=cut
sub peer_name {
    my $self  = shift;
    my $value = shift;

    if(defined $value and $value ne '') {
        $self->{'name'} = $value;
    }

    return "".$self->{'name'};
}


########################################

=head2 peer_key

 $nl->peer_key()

returns a uniq key for this peer

when using multiple backends, a list of all keys is returned in list context

=cut
sub peer_key {
    my $self  = shift;

    if(!defined $self->{'key'}) { $self->{'key'} = md5_hex($self->peer_addr." ".$self->peer_name); }

    return $self->{'key'};
}


########################################

=head2 marked_bad

 $nl->marked_bad()

returns true if the current connection is marked down

=cut
sub marked_bad {
    my $self  = shift;

    return 0;
}


########################################
# INTERNAL SUBS
########################################
sub _send {
    my $self       = shift;
    my $statement  = shift;
    my $with_peers = shift;
    my $header     = "";
    my $keys;

    $Nagios::MKLivestatus::ErrorCode = 0;
    undef $Nagios::MKLivestatus::ErrorMessage;

    return(490, $self->_get_error(490), undef) if !defined $statement;
    chomp($statement);

    # remove empty lines from statement
    $statement =~ s/\n+/\n/gmx;

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

        # for querys with column header, no seperate columns will be returned
        if($statement =~ m/^Columns:\ (.*)$/mx) {
            ($statement,$keys) = $self->_extract_keys_from_columns_header($statement);
        } elsif($statement =~ m/^Stats:\ (.*)$/mx or $statement =~ m/^StatsGroupBy:\ (.*)$/mx) {
            ($statement,$keys) = $self->_extract_keys_from_stats_statement($statement);
        }

        # Commands need no additional header
        if($statement !~ m/^COMMAND/mx) {
            $header .= "Separators: $self->{'line_seperator'} $self->{'column_seperator'} $self->{'list_seperator'} $self->{'host_service_seperator'}\n";
            $header .= "ResponseHeader: fixed16\n";
            if($self->{'keepalive'}) {
                $header .= "KeepAlive: on\n";
            }
        }
        chomp($statement);
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
        $self->{'logger'}->error($status." - ".$Nagios::MKLivestatus::ErrorMessage." in query:\n'".$statement) if defined $self->{'logger'};
        if($self->{'errors_are_fatal'}) {
            croak("ERROR ".$status." - ".$Nagios::MKLivestatus::ErrorMessage." in query:\n'".$statement."'\n");
        }
        return;
    }

    # return a empty result set if nothing found
    return({ keys => [], result => []}) if !defined $body;

    my $line_seperator = chr($self->{'line_seperator'});
    my $col_seperator  = chr($self->{'column_seperator'});

    my $peer_name = $self->peer_name;
    my $peer_addr = $self->peer_addr;
    my $peer_key  = $self->peer_key;

    my @result;
    ## no critic
    for my $line (split/$line_seperator/m, $body) {
        my $row = [ split/$col_seperator/m, $line ];
        if(defined $with_peers and $with_peers == 1) {
            unshift @{$row}, $peer_name;
            unshift @{$row}, $peer_addr;
            unshift @{$row}, $peer_key;
        }
        push @result, $row;
    }
    ## use critic

    # for querys with column header, no seperate columns will be returned
    if(!defined $keys) {
        $self->{'logger'}->warn("got statement without Columns: header!") if defined $self->{'logger'};
        if($self->{'warnings'}) {
            carp("got statement without Columns: header! -> ".$statement);
        }
        $keys = shift @result;

        # remove first element of keys, because its the peer_name
        if(defined $with_peers and $with_peers == 1) {
            shift @{$keys};
            shift @{$keys};
            shift @{$keys};
        }
    }

    if(defined $with_peers and $with_peers == 1) {
        unshift @{$keys}, 'peer_name';
        unshift @{$keys}, 'peer_addr';
        unshift @{$keys}, 'peer_key';
    }

    return({ keys => $keys, result => \@result});
}

########################################
sub _open {
    my $self      = shift;
    my $statement = shift;

    # return the current socket in keep alive mode
    if($self->{'keepalive'} and defined $self->{'sock'} and $self->{'sock'}->atmark()) {
        return($self->{'sock'});
    }

    my $sock = $self->{'CONNECTOR'}->_open();

    # store socket for later retrieval
    if($self->{'keepalive'}) {
        $self->{'sock'} = $sock;
    }

    # set timeout
    $sock->timeout($self->{'timeout'}) if defined $sock;

    return($sock);
}

########################################
sub _close {
    my $self  = shift;
    my $sock  = shift;
    return($self->{'CONNECTOR'}->_close($sock));
}


########################################

=head1 QUERY OPTIONS

In addition to the normal query syntax from the livestatus addon, it is
possible to set column aliases in various ways.

=head2 AddPeer

adds the peers name, addr and key to the result set:

 my $hosts = $nl->selectall_hashref(
   "GET hosts\nColumns: name alias state",
   "name",
   { AddPeer => 1 }
 );

=head2 Backend

send the query only to some specific backends. Only
useful when using multiple backends.

 my $hosts = $nl->selectall_arrayref(
   "GET hosts\nColumns: name alias state",
   { Backends => [ 'key1', 'key4' ] }
 );

=head2 Columns

    only return the given column indexes

    my $array_ref = $nl->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Columns => [2] }
    );

  see L<selectcol_arrayref> for more examples

=head2 Rename

  see L<COLUMN ALIAS> for detailed explainaton

=head2 Slice

  see L<selectall_arrayref> for detailed explainaton

=head2 Sum

The Sum option only applies when using multiple backends.
The values from all backends with be summed up to a total.

 my $stats = $nl->selectrow_hashref(
   "GET hosts\nStats: state = 0\nStats: state = 1",
   { Sum => 1 }
 );

=cut


########################################
sub _send_socket {
    my $self      = shift;
    my $statement = shift;
    my($recv,$header);

    my $sock = $self->_open() or return(491, $self->_get_error(491), $!);
    print $sock $statement or return($self->_socket_error($statement, $sock, 'connection failed: '.$!));;
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

    $sock->read($header, 16) or return($self->_socket_error($statement, $sock, 'reading header failed: '.$!));
    print "header: $header" if $self->{'verbose'};
    my($status, $msg, $content_length) = $self->_parse_header($header, $sock);
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
    $message   .= "peer                ".Dumper($self->peer_name);
    $message   .= "statement           ".Dumper($statement);
    $message   .= "socket->sockname()  ".Dumper($sock->sockname());
    $message   .= "socket->atmark()    ".Dumper($sock->atmark());
    $message   .= "socket->error()     ".Dumper($sock->error());
    $message   .= "socket->timeout()   ".Dumper($sock->timeout());
    $message   .= "message             ".Dumper($body);

    $self->{'logger'}->error($message) if defined $self->{'logger'};

    if($self->{'errors_are_fatal'}) {
        croak($message);
    } else {
        carp($message);
    }
    return(500, $self->_get_error(500), $message);
}

########################################
sub _parse_header {
    my $self   = shift;
    my $header = shift;
    my $sock   = shift;

    if(!defined $header) {
        return(497, $self->_get_error(497), undef);
    }

    my $headerlength = length($header);
    if($headerlength != 16) {
        return(498, $self->_get_error(498)."\ngot: ".$header.<$sock>, undef);
    }
    chomp($header);

    my $status         = substr($header,0,3);
    my $content_length = substr($header,5);
    if($content_length !~ m/^\s*(\d+)$/mx) {
        return(499, $self->_get_error(499)."\ngot: ".$header.<$sock>, undef);
    } else {
        $content_length = $1;
    }

    return($status, $self->_get_error($status), $content_length);
}

########################################

=head1 COLUMN ALIAS

In addition to the normal query syntax from the livestatus addon, it is
possible to set column aliases in various ways.

A valid Columns: Header could look like this:

 my $hosts = $nl->selectall_arrayref(
   "GET hosts\nColumns: state as status"
 );

Stats queries could be aliased too:

 my $stats = $nl->selectall_arrayref(
   "GET hosts\nStats: state = 0 as up"
 );

This syntax is available for: Stats, StatsAnd, StatsOr and StatsGroupBy


An alternative way to set column aliases is to define rename option key/value
pairs:

 my $hosts = $nl->selectall_arrayref(
   "GET hosts\nColumns: name", {
     rename => { 'name' => 'hostname' }
   }
 );

=cut

########################################
sub _extract_keys_from_stats_statement {
    my $self      = shift;
    my $statement = shift;

    my(@header, $new_statement);

    for my $line (split/\n/mx, $statement) {
        if($line =~ m/^Stats:\ (.*)\s+as\s+(.*)$/mxi) {
            push @header, $2;
            $line = 'Stats: '.$1;
        }
        elsif($line =~ m/^Stats:\ (.*)$/mx) {
            push @header, $1;
        }

        if($line =~ m/^StatsAnd:\ (\d+)\s+as\s+(.*)$/mx) {
            for(my $x = 0; $x < $1; $x++) {
                pop @header;
            }
            $line = 'StatsAnd: '.$1;
            push @header, $2;
        }
        elsif($line =~ m/^StatsAnd:\ (\d+)$/mx) {
            my @to_join;
            for(my $x = 0; $x < $1; $x++) {
                unshift @to_join, pop @header;
            }
            push @header, join(' && ', @to_join);
        }

        if($line =~ m/^StatsOr:\ (\d+)\s+as\s+(.*)$/mx) {
            for(my $x = 0; $x < $1; $x++) {
                pop @header;
            }
            $line = 'StatsOr: '.$1;
            push @header, $2;
        }
        elsif($line =~ m/^StatsOr:\ (\d+)$/mx) {
            my @to_join;
            for(my $x = 0; $x < $1; $x++) {
                unshift @to_join, pop @header;
            }
            push @header, join(' || ', @to_join);
        }

        # StatsGroupBy header are always sent first
        if($line =~ m/^StatsGroupBy:\ (.*)\s+as\s+(.*)$/mxi) {
            unshift @header, $2;
            $line = 'StatsGroupBy: '.$1;
        }
        elsif($line =~ m/^StatsGroupBy:\ (.*)$/mx) {
            unshift @header, $1;
        }
        $new_statement .= $line."\n";
    }

    return($new_statement, \@header);
}

########################################
sub _extract_keys_from_columns_header {
    my $self      = shift;
    my $statement = shift;

    my(@header, $new_statement);
    for my $line (split/\n/mx, $statement) {
        if($line =~ m/^Columns:\s+(.*)$/mx) {
            for my $column (split/\s+/mx, $1) {
                if($column eq 'as') {
                    pop @header;
                } else {
                    push @header, $column;
                }
            }
            $line =~ s/\s+as\s+([^\s]+)/\ /gmx;
        }
        $new_statement .= $line."\n";
    }

    return($new_statement, \@header);
}

########################################

=head1 ERROR HANDLING

Errorhandling can be done like this:

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus->new(
      socket => '/var/lib/nagios3/rw/livestatus.sock'
    );
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
        '499' => 'not a valid header (no content-length)',
        '500' => 'socket error',
    };

    confess('non existant error code: '.$code) if !defined $codes->{$code};

    return($codes->{$code});
}

########################################
sub _get_peers {
    my $self   = shift;

    # set options for our peer(s)
    my %options;
    for my $opt_key (keys %{$self}) {
        $options{$opt_key} = $self->{$opt_key};
    }

    my $peers = [];

    # check if the supplied peer is a socket or a server address
    if(defined $self->{'peer'}) {
        if(ref $self->{'peer'} eq '') {
            my $name = $self->{'name'} || "".$self->{'peer'};
            if(index($self->{'peer'}, ':') > 0) {
                push @{$peers}, { 'peer' => "".$self->{'peer'}, type => 'INET', name => $name };
            } else {
                push @{$peers}, { 'peer' => "".$self->{'peer'}, type => 'UNIX', name => $name };
            }
        }
        elsif(ref $self->{'peer'} eq 'ARRAY') {
            for my $peer (@{$self->{'peer'}}) {
                if(ref $peer eq 'HASH') {
                    next if !defined $peer->{'peer'};
                    $peer->{'name'} = "".$peer->{'peer'} unless defined $peer->{'name'};
                    if(!defined $peer->{'type'}) {
                        $peer->{'type'} = 'UNIX';
                        if(index($peer->{'peer'}, ':') >= 0) {
                            $peer->{'type'} = 'INET';
                        }
                    }
                    push @{$peers}, $peer;
                } else {
                    my $type = 'UNIX';
                    if(index($peer, ':') >= 0) {
                        $type = 'INET';
                    }
                    push @{$peers}, { 'peer' => "".$peer, type => $type, name => "".$peer };
                }
            }
        }
        elsif(ref $self->{'peer'} eq 'HASH') {
            for my $peer (keys %{$self->{'peer'}}) {
                my $name = $self->{'peer'}->{$peer};
                my $type = 'UNIX';
                if(index($peer, ':') >= 0) {
                    $type = 'INET';
                }
                push @{$peers}, { 'peer' => "".$peer, type => $type, name => "".$name };
            }
        } else {
            confess("type ".(ref $self->{'peer'})." is not supported for peer option");
        }
    }
    if(defined $self->{'socket'}) {
        my $name = $self->{'name'} || "".$self->{'socket'};
        push @{$peers}, { 'peer' => "".$self->{'socket'}, type => 'UNIX', name => $name };
    }
    if(defined $self->{'server'}) {
        my $name = $self->{'name'} || "".$self->{'server'};
        push @{$peers}, { 'peer' => "".$self->{'server'}, type => 'INET', name => $name };
    }

    # check if we got a peer
    if(scalar @{$peers} == 0) {
        croak('please specify at least one peer, socket or server');
    }

    # clean up
    delete $options{'peer'};
    delete $options{'socket'};
    delete $options{'server'};

    return $peers;
}

1;

=head1 EXAMPLES

=head2 Multibackend Configuration

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus->new(
      name       => 'multiple connector',
      verbose   => 0,
      keepalive => 1,
      peer      => [
            {
                name => 'DMZ Nagios',
                peer => '50.50.50.50:9999',
            },
            {
                name => 'Local Nagios',
                peer => '/tmp/livestatus.socket',
            },
            {
                name => 'Special Nagios',
                peer => '100.100.100.100:9999',
            }
      ],
    );
    my $hosts = $nl->selectall_arrayref("GET hosts");

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
