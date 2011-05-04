package Monitoring::Livestatus;

use 5.006;
use strict;
use warnings;
use Data::Dumper;
use Carp;
use Digest::MD5 qw(md5_hex);
use Monitoring::Livestatus::INET;
use Monitoring::Livestatus::UNIX;
use Monitoring::Livestatus::MULTI;
use Encode;
use JSON::XS;

our $VERSION = '0.74';


=head1 NAME

Monitoring::Livestatus - Perl API for check_mk livestatus to access runtime
data from Nagios and Icinga

=head1 SYNOPSIS

    use Monitoring::Livestatus;
    my $ml = Monitoring::Livestatus->new(
      socket => '/var/lib/livestatus/livestatus.sock'
    );
    my $hosts = $ml->selectall_arrayref("GET hosts");

=head1 DESCRIPTION

This module connects via socket/tcp to the check_mk livestatus addon for Nagios
and Icinga. You first have to install and activate the mklivestatus addon in your
monitoring installation.

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Monitoring::Livestatus> object. C<new> takes at least the
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

set a general timeout. Used for connect and querys, no default

=item query_timeout

set a query timeout. Used for retrieving querys, Default 60sec

=item connect_timeout

set a connect timeout. Used for initial connections, default 5sec

=item use_threads

only used with multiple backend connections.
Default is to don't threads where available. As threads in perl
are causing problems with tied resultset and using more memory.
Querys are usually faster without threads, except for very slow backends
connections.

=back

If the constructor is only passed a single argument, it is assumed to
be a the C<peer> specification. Use either socker OR server.

=cut

sub new {
    my $class = shift;
    unshift(@_, "peer") if scalar @_ == 1;
    my(%options) = @_;

    my $self = {
      "verbose"                     => 0,       # enable verbose output
      "socket"                      => undef,   # use unix sockets
      "server"                      => undef,   # use tcp connections
      "peer"                        => undef,   # use for socket / server connections
      "name"                        => undef,   # human readable name
      "line_seperator"              => 10,      # defaults to newline
      "column_seperator"            => 0,       # defaults to null byte
      "list_seperator"              => 44,      # defaults to comma
      "host_service_seperator"      => 124,     # defaults to pipe
      "keepalive"                   => 0,       # enable keepalive?
      "errors_are_fatal"            => 1,       # die on errors
      "backend"                     => undef,   # should be keept undef, used internally
      "timeout"                     => undef,   # timeout for tcp connections
      "query_timeout"               => 60,      # query timeout for tcp connections
      "connect_timeout"             => 5,       # connect timeout for tcp connections
      "timeout"                     => undef,   # timeout for tcp connections
      "use_threads"                 => undef,   # use threads, default is to use threads where available
      "warnings"                    => 1,       # show warnings, for example on querys without Column: Header
      "logger"                      => undef,   # logger object used for statistical informations and errors / warnings
      "deepcopy"                    => undef,   # copy result set to avoid errors with tied structures
      "disabled"                    => 0,       # if disabled, this peer will not receive any query
      "retries_on_connection_error" => 3,       # retry x times to connect
      "retry_interval"              => 1,       # retry after x seconds
    };

    for my $opt_key (keys %options) {
        if(exists $self->{$opt_key}) {
            $self->{$opt_key} = $options{$opt_key};
        }
        else {
            croak("unknown option: $opt_key");
        }
    }

    if($self->{'verbose'} and !defined $self->{'logger'}) {
        croak('please specify a logger object when using verbose mode');
        $self->{'verbose'} = 0;
    }

    # setting a general timeout?
    if(defined $self->{'timeout'}) {
        $self->{'query_timeout'}   = $self->{'timeout'};
        $self->{'connect_timeout'} = $self->{'timeout'};
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
                $self->{'CONNECTOR'} = new Monitoring::Livestatus::UNIX(%options);
            }
            elsif($peer->{'type'} eq 'INET') {
                $self->{'CONNECTOR'} = new Monitoring::Livestatus::INET(%options);
            }
            $self->{'peer'} = $peer->{'peer'};
        }
        else {
            $options{'peer'} = $peers;
            return new Monitoring::Livestatus::MULTI(%options);
        }
    }

    # set names and peer for non multi backends
    if(defined $self->{'CONNECTOR'}->{'name'} and !defined $self->{'name'}) {
        $self->{'name'} = $self->{'CONNECTOR'}->{'name'};
    }
    if(defined $self->{'CONNECTOR'}->{'peer'} and !defined $self->{'peer'}) {
        $self->{'peer'} = $self->{'CONNECTOR'}->{'peer'};
    }

    if($self->{'verbose'} and (!defined $self->{'backend'} or $self->{'backend'} ne 'Monitoring::Livestatus::MULTI')) {
        $self->{'logger'}->debug('initialized Monitoring::Livestatus ('.$self->peer_name.')');
    }

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
    return if $self->{'disabled'};
    $self->_send($statement);
    return(1);
}


########################################

=head2 selectall_arrayref

 selectall_arrayref($statement)
 selectall_arrayref($statement, %opts)
 selectall_arrayref($statement, %opts, $limit )

Sends a query and returns an array reference of arrays

    my $arr_refs = $ml->selectall_arrayref("GET hosts");

to get an array of hash references do something like

    my $hash_refs = $ml->selectall_arrayref(
      "GET hosts", { Slice => {} }
    );

to get an array of hash references from the first 2 returned rows only

    my $hash_refs = $ml->selectall_arrayref(
      "GET hosts", { Slice => {} }, 2
    );

use limit to limit the result to this number of rows

column aliases can be defined with a rename hash

    my $hash_refs = $ml->selectall_arrayref(
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
    return if $self->{'disabled'};
    my $result;

    # make opt hash keys lowercase
    $opt = $self->_lowercase_and_verify_options($opt);

    $self->_log_statement($statement, $opt, $limit) if $self->{'verbose'};

    $result = $self->_send($statement, $opt);

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
            # add callbacks
            if(exists $opt->{'callbacks'}) {
                for my $key (keys %{$opt->{'callbacks'}}) {
                    $hash_ref->{$key} = $opt->{'callbacks'}->{$key}->($hash_ref);
                }
            }
            push @hash_refs, $hash_ref;
        }
        return(\@hash_refs);
    }
    elsif(exists $opt->{'callbacks'}) {
        for my $res (@{$result->{'result'}}) {
            # add callbacks
            if(exists $opt->{'callbacks'}) {
                for my $key (keys %{$opt->{'callbacks'}}) {
                    push @{$res}, $opt->{'callbacks'}->{$key}->($res);
                }
            }
        }
    }

    if(exists $opt->{'callbacks'}) {
        for my $key (keys %{$opt->{'callbacks'}}) {
            push @{$result->{'keys'}}, $key;
        }
    }

    return($result->{'result'});
}


########################################

=head2 selectall_hashref

 selectall_hashref($statement, $key_field)
 selectall_hashref($statement, $key_field, %opts)

Sends a query and returns a hashref with the given key

    my $hashrefs = $ml->selectall_hashref("GET hosts", "name");

=cut

sub selectall_hashref {
    my $self      = shift;
    my $statement = shift;
    my $key_field = shift;
    my $opt       = shift;

    $opt = $self->_lowercase_and_verify_options($opt);

    $opt->{'slice'} = 1;

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

    my $array_ref = $ml->selectcol_arrayref("GET hosts\nColumns: name");

    $VAR1 = [
              'localhost',
              'gateway',
            ];

returns an empty array if nothing was found

to get a different column use this

    my $array_ref = $ml->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Columns => [2] }
    );

 you can link 2 columns in a hash result set

    my %hash = @{
      $ml->selectcol_arrayref(
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
    $opt = $self->_lowercase_and_verify_options($opt);

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

    my @array = $ml->selectrow_array("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_array {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    # make opt hash keys lowercase
    $opt = $self->_lowercase_and_verify_options($opt);

    my @result = @{$self->selectall_arrayref($statement, $opt, 1)};
    return @{$result[0]} if scalar @result > 0;
    return;
}


########################################

=head2 selectrow_arrayref

 selectrow_arrayref($statement)
 selectrow_arrayref($statement, %opts)

Sends a query and returns an array reference for the first row

    my $arrayref = $ml->selectrow_arrayref("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_arrayref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    # make opt hash keys lowercase
    $opt = $self->_lowercase_and_verify_options($opt);

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

    my $hashref = $ml->selectrow_hashref("GET hosts");

returns undef if nothing was found

=cut
sub selectrow_hashref {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    # make opt hash keys lowercase
    $opt = $self->_lowercase_and_verify_options($opt);
    $opt->{slice} = 1;

    my $result = $self->selectall_arrayref($statement, $opt, 1);
    return if !defined $result;
    return $result->[0] if scalar @{$result} > 0;
    return;
}


########################################

=head2 selectscalar_value

 selectscalar_value($statement)
 selectscalar_value($statement, %opt)

Sends a query and returns a single scalar

    my $count = $ml->selectscalar_value("GET hosts\nStats: state = 0");

returns undef if nothing was found

=cut
sub selectscalar_value {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;

    # make opt hash keys lowercase
    $opt = $self->_lowercase_and_verify_options($opt);

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

 $ml->peer_addr()

returns the current peer address

when using multiple backends, a list of all addresses is returned in list context

=cut
sub peer_addr {
    my $self  = shift;

    return "".$self->{'peer'};
}


########################################

=head2 peer_name

 $ml->peer_name()
 $ml->peer_name($string)

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

 $ml->peer_key()

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

 $ml->marked_bad()

returns true if the current connection is marked down

=cut
sub marked_bad {
    my $self  = shift;

    return 0;
}


########################################

=head2 disable

 $ml->disable()

disables this connection, returns the last state.

=cut
sub disable {
    my $self  = shift;
    my $prev = $self->{'disabled'};
    $self->{'disabled'} = 1;
    return $prev;
}


########################################

=head2 enable

 $ml->enable()

enables this connection, returns the last state.

=cut
sub enable {
    my $self  = shift;
    my $prev = $self->{'disabled'};
    $self->{'disabled'} = 0;
    return $prev;
}

########################################
# INTERNAL SUBS
########################################
sub _send {
    my $self       = shift;
    my $statement  = shift;
    my $opt        = shift;

    delete $self->{'meta_data'};

    my $header     = "";
    my $keys;

    my $with_peers = 0;
    if(defined $opt->{'addpeer'} and $opt->{'addpeer'}) {
        $with_peers = 1;
    }

    $Monitoring::Livestatus::ErrorCode = 0;
    undef $Monitoring::Livestatus::ErrorMessage;

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

        # Add Limits header
        if(defined $opt->{'limit_start'}) {
            $statement .= "\nLimit: ".($opt->{'limit_start'} + $opt->{'limit_length'});
        }

        # for querys with column header, no seperate columns will be returned
        if($statement =~ m/^Columns:\ (.*)$/mx) {
            ($statement,$keys) = $self->_extract_keys_from_columns_header($statement);
        } elsif($statement =~ m/^Stats:\ (.*)$/mx or $statement =~ m/^StatsGroupBy:\ (.*)$/mx) {
            ($statement,$keys) = $self->_extract_keys_from_stats_statement($statement);
        }

        # Commands need no additional header
        if($statement !~ m/^COMMAND/mx) {
            $header .= "OutputFormat: json\n";
            $header .= "ResponseHeader: fixed16\n";
            if($self->{'keepalive'}) {
                $header .= "KeepAlive: on\n";
            }
            # remove empty lines from statement
            $statement =~ s/\n+/\n/gmx;
        }

        # add additional headers
        if(defined $opt->{'header'} and ref $opt->{'header'} eq 'HASH') {
            for my $key ( keys %{$opt->{'header'}}) {
                $header .= $key.": ".$opt->{'header'}->{$key}."\n";
            }
        }

        chomp($statement);
        my $send = "$statement\n$header";
        $self->{'logger'}->debug("> ".Dumper($send)) if $self->{'verbose'};
        ($status,$msg,$body) = $self->_send_socket($send);
        if($self->{'verbose'}) {
            #$self->{'logger'}->debug("got:");
            #$self->{'logger'}->debug(Dumper(\@erg));
            $self->{'logger'}->debug("status: ".Dumper($status));
            $self->{'logger'}->debug("msg:    ".Dumper($msg));
            $self->{'logger'}->debug("< ".Dumper($body));
        }
    }

    if($status >= 300) {
        $body = '' if !defined $body;
        chomp($body);
        $Monitoring::Livestatus::ErrorCode    = $status;
        if(defined $body and $body ne '') {
            $Monitoring::Livestatus::ErrorMessage = $body;
        } else {
            $Monitoring::Livestatus::ErrorMessage = $msg;
        }
        $self->{'logger'}->error($status." - ".$Monitoring::Livestatus::ErrorMessage." in query:\n'".$statement) if $self->{'verbose'};
        if($self->{'errors_are_fatal'}) {
            croak("ERROR ".$status." - ".$Monitoring::Livestatus::ErrorMessage." in query:\n'".$statement."'\n");
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

    my $limit_start = 0;
    if(defined $opt->{'limit_start'}) { $limit_start = $opt->{'limit_start'}; }
    my $result;
    # fix json output
    $body =~ s/\],\n\]\n$/]]/mx;
    eval {
        $result = decode_json($body);
    };
    if($@) {
        my $message = "ERROR ".$@." in text: '".$body."'\" for statement: '$statement'\n";
        $self->{'logger'}->error($message) if $self->{'verbose'};
        if($self->{'errors_are_fatal'}) {
            croak($message);
        }
    }

    # for querys with column header, no separate columns will be returned
    if(!defined $keys) {
        $self->{'logger'}->warn("got statement without Columns: header!") if $self->{'verbose'};
        if($self->{'warnings'}) {
            carp("got statement without Columns: header! -> ".$statement);
        }
        $keys = shift @{$result};
    }

    # add peer information?
    if(defined $with_peers and $with_peers == 1) {
        unshift @{$keys}, 'peer_name';
        unshift @{$keys}, 'peer_addr';
        unshift @{$keys}, 'peer_key';

        for my $row (@{$result}) {
            unshift @{$row}, $peer_name;
            unshift @{$row}, $peer_addr;
            unshift @{$row}, $peer_key;
        }
    }

    # set some metadata
    $self->{'meta_data'} = {
                    'result_count' => scalar @${result},
    };

    return({ keys => $keys, result => $result });
}

########################################
sub _open {
    my $self      = shift;
    my $statement = shift;

    # return the current socket in keep alive mode
    if($self->{'keepalive'} and defined $self->{'sock'} and $self->{'sock'}->connected) {
        $self->{'logger'}->debug("reusing old connection") if $self->{'verbose'};
        return($self->{'sock'});
    }

    my $sock = $self->{'CONNECTOR'}->_open();

    # store socket for later retrieval
    if($self->{'keepalive'}) {
        $self->{'sock'} = $sock;
    }

    $self->{'logger'}->debug("using new connection") if $self->{'verbose'};
    return($sock);
}

########################################
sub _close {
    my $self  = shift;
    my $sock  = shift;
    undef $self->{'sock'};
    return($self->{'CONNECTOR'}->_close($sock));
}


########################################

=head1 QUERY OPTIONS

In addition to the normal query syntax from the livestatus addon, it is
possible to set column aliases in various ways.

=head2 AddPeer

adds the peers name, addr and key to the result set:

 my $hosts = $ml->selectall_hashref(
   "GET hosts\nColumns: name alias state",
   "name",
   { AddPeer => 1 }
 );

=head2 Backend

send the query only to some specific backends. Only
useful when using multiple backends.

 my $hosts = $ml->selectall_arrayref(
   "GET hosts\nColumns: name alias state",
   { Backends => [ 'key1', 'key4' ] }
 );

=head2 Columns

    only return the given column indexes

    my $array_ref = $ml->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Columns => [2] }
    );

  see L<selectcol_arrayref> for more examples

=head2 Deepcopy

    deep copy/clone the result set.

    Only effective when using multiple backends and threads.
    This can be safely turned off if you dont change the
    result set.
    If you get an error like "Invalid value for shared scalar" error" this
    should be turned on.

    my $array_ref = $ml->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Deepcopy => 1 }
    );

=head2 Limit

    Just like the Limit: <nr> option from livestatus itself.
    In addition you can add a start,length limit.

    my $array_ref = $ml->selectcol_arrayref(
       "GET hosts\nColumns: name contacts",
       { Limit => "10,20" }
    );

    This example will return 20 rows starting at row 10. You will
    get row 10-30.

    Cannot be combined with a Limit inside the query
    because a Limit will be added automatically.

    Adding a limit this way will greatly increase performance and
    reduce memory usage.

    This option is multibackend safe contrary to the "Limit: " part of a statement.
    Sending a statement like "GET...Limit: 10" with 3 backends will result in 30 rows.
    Using this options, you will receive only the first 10 rows.

=head2 Rename

  see L<COLUMN ALIAS> for detailed explainaton

=head2 Slice

  see L<selectall_arrayref> for detailed explainaton

=head2 Sum

The Sum option only applies when using multiple backends.
The values from all backends with be summed up to a total.

 my $stats = $ml->selectrow_hashref(
   "GET hosts\nStats: state = 0\nStats: state = 1",
   { Sum => 1 }
 );

=cut


########################################
# wrapper around _send_socket_do
sub _send_socket {
    my $self      = shift;
    my $statement = shift;

    my $retries = 0;
    my($status, $msg, $recv);


    # try to avoid connection errors
    eval {
        local $SIG{PIPE} = sub {
            die("broken pipe");
            $self->{'logger'}->debug("broken pipe, closing socket") if $self->{'verbose'};
            $self->_close($self->{'sock'});
        };

        if($self->{'retries_on_connection_error'} <= 0) {
            ($status, $msg, $recv) = $self->_send_socket_do($statement);
            return;
        }

        while((!defined $status or ($status == 491 or $status == 497 or $status == 500)) and $retries < $self->{'retries_on_connection_error'}) {
            $retries++;
            ($status, $msg, $recv) = $self->_send_socket_do($statement);
            $self->{'logger'}->debug('query status '.$status) if $self->{'verbose'};
            if($status == 491 or $status == 497 or $status == 500) {
                $self->{'logger'}->debug('got status '.$status.' retrying in '.$self->{'retry_interval'}.' seconds') if $self->{'verbose'};
                $self->_close();
                sleep($self->{'retry_interval'}) if $retries < $self->{'retries_on_connection_error'};
            }
        }
    };
    if($@) {
        $self->{'logger'}->debug("try 1 failed: $@") if $self->{'verbose'};
        if(defined $@ and $@ =~ /broken\ pipe/mx) {
            return $self->_send_socket_do($statement);
        }
        croak($@) if $self->{'errors_are_fatal'};
    }

    croak($msg) if($status >= 400 and $self->{'errors_are_fatal'});

    return($status, $msg, $recv);
}

########################################
sub _send_socket_do {
    my $self      = shift;
    my $statement = shift;
    my($recv,$header);

    my $sock = $self->_open() or return(491, $self->_get_error(491), $!);
    utf8::decode($statement);
    print $sock encode('utf-8' => $statement) or return($self->_socket_error($statement, $sock, 'write to socket failed: '.$!));

    print $sock "\n";

    # COMMAND statements never return something
    if($statement =~ m/^COMMAND/mx) {
        return('201', $self->_get_error(201), undef);
    }

    $sock->read($header, 16) or return($self->_socket_error($statement, $sock, 'reading header from socket failed, check your livestatus logfile: '.$!));
    $self->{'logger'}->debug("header: $header") if $self->{'verbose'};
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
    $message   .= "message             ".Dumper($body);

    $self->{'logger'}->error($message) if $self->{'verbose'};

    if($self->{'retries_on_connection_error'} <= 0) {
        if($self->{'errors_are_fatal'}) {
            croak($message);
        }
        else {
            carp($message);
        }
    }
    $self->_close();
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

 my $hosts = $ml->selectall_arrayref(
   "GET hosts\nColumns: state as status"
 );

Stats queries could be aliased too:

 my $stats = $ml->selectall_arrayref(
   "GET hosts\nStats: state = 0 as up"
 );

This syntax is available for: Stats, StatsAnd, StatsOr and StatsGroupBy


An alternative way to set column aliases is to define rename option key/value
pairs:

 my $hosts = $ml->selectall_arrayref(
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

    use Monitoring::Livestatus;
    my $ml = Monitoring::Livestatus->new(
      socket => '/var/lib/livestatus/livestatus.sock'
    );
    $ml->errors_are_fatal(0);
    my $hosts = $ml->selectall_arrayref("GET hosts");
    if($Monitoring::Livestatus::ErrorCode) {
        croak($Monitoring::Livestatus::ErrorMessage);
    }

=cut
sub _get_error {
    my $self = shift;
    my $code = shift;

    my $codes = {
        '200' => 'OK. Reponse contains the queried data.',
        '201' => 'COMMANDs never return something',
        '400' => 'The request contains an invalid header.',
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


########################################
sub _lowercase_and_verify_options {
    my $self   = shift;
    my $opts   = shift;
    my $return = {};

    # list of allowed options
    my $allowed_options = {
        'addpeer'       => 1,
        'backend'       => 1,
        'columns'       => 1,
        'deepcopy'      => 1,
        'header'        => 1,
        'limit'         => 1,
        'limit_start'   => 1,
        'limit_length'  => 1,
        'rename'        => 1,
        'slice'         => 1,
        'sum'           => 1,
        'callbacks'     => 1,
    };

    for my $key (keys %{$opts}) {
        if($self->{'warnings'} and !defined $allowed_options->{lc $key}) {
            carp("unknown option used: $key - please use only: ".join(", ", keys %{$allowed_options}));
        }
        $return->{lc $key} = $opts->{$key};
    }

    # set limits
    if(defined $return->{'limit'}) {
        if(index($return->{'limit'}, ',') != -1) {
            my($limit_start,$limit_length) = split /,/mx, $return->{'limit'};
            $return->{'limit_start'}  = $limit_start;
            $return->{'limit_length'} = $limit_length;
        }
        else {
            $return->{'limit_start'}  = 0;
            $return->{'limit_length'} = $return->{'limit'};
        }
        delete $return->{'limit'};
    }

    return($return);
}

########################################
sub _log_statement {
    my $self      = shift;
    my $statement = shift;
    my $opt       = shift;
    my $limit     = shift;
    my $d = Data::Dumper->new([$opt]);
    $d->Indent(0);
    my $optstring = $d->Dump;
    $optstring =~ s/^\$VAR1\s+=\s+//mx;
    $optstring =~ s/;$//mx;

    # remove empty lines from statement
    $statement =~ s/\n+/\n/gmx;

    my $cleanstatement = $statement;
    $cleanstatement =~ s/\n/\\n/gmx;
    $self->{'logger'}->debug('selectall_arrayref("'.$cleanstatement.'", '.$optstring.', '.$limit.')');
    return 1;
}

########################################

1;

=head1 EXAMPLES

=head2 Multibackend Configuration

    use Monitoring::Livestatus;
    my $ml = Monitoring::Livestatus->new(
      name       => 'multiple connector',
      verbose   => 0,
      keepalive => 1,
      peer      => [
            {
                name => 'DMZ Monitoring',
                peer => '50.50.50.50:9999',
            },
            {
                name => 'Local Monitoring',
                peer => '/tmp/livestatus.socket',
            },
            {
                name => 'Special Monitoring',
                peer => '100.100.100.100:9999',
            }
      ],
    );
    my $hosts = $ml->selectall_arrayref("GET hosts");

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
