package Monitoring::Livestatus::MULTI;

use 5.000000;
use strict;
use warnings;
use Carp;
use Data::Dumper;
use Config;
use Time::HiRes qw/gettimeofday tv_interval/;
use Scalar::Util qw/looks_like_number/;
use Monitoring::Livestatus;
use base "Monitoring::Livestatus";

=head1 NAME

Monitoring::Livestatus::MULTI - connector with multiple peers

=head1 SYNOPSIS

    use Monitoring::Livestatus;
    my $nl = Monitoring::Livestatus::MULTI->new( qw{nagioshost1:9999 nagioshost2:9999 /var/spool/nagios/live.socket} );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Monitoring::Livestatus::MULTI> object. C<new> takes at least the server.
Arguments are the same as in L<Monitoring::Livestatus>.

=cut

sub new {
    my $class = shift;
    unshift(@_, "peer") if scalar @_ == 1;
    my(%options) = @_;

    $options{'backend'} = $class;
    my $self = Monitoring::Livestatus->new(%options);
    bless $self, $class;

    if(!defined $self->{'peers'}) {
        $self->{'peer'} = $self->_get_peers();

        # set our peer(s) from the options
        my %peer_options;
        my $peers;
        for my $opt_key (keys %options) {
            $peer_options{$opt_key} = $options{$opt_key};
        }
        $peer_options{'errors_are_fatal'} = 0;
        for my $peer (@{$self->{'peer'}}) {
            $peer_options{'name'} = $peer->{'name'};
            $peer_options{'peer'} = $peer->{'peer'};
            delete $peer_options{'socket'};
            delete $peer_options{'server'};

            if($peer->{'type'} eq 'UNIX') {
                push @{$peers}, new Monitoring::Livestatus::UNIX(%peer_options);
            }
            elsif($peer->{'type'} eq 'INET') {
                push @{$peers}, new Monitoring::Livestatus::INET(%peer_options);
            }
        }
        $self->{'peers'} = $peers;
        delete $self->{'socket'};
        delete $self->{'server'};
    }

    if(!defined $self->{'peers'}) {
        croak('please specify at least one peer, socket or server');
    }

    # dont use threads with only one peer
    if(scalar @{$self->{'peers'}} == 1) { $self->{'use_threads'} = 0; }

    # check for threads support
    if(!defined $self->{'use_threads'}) {
        $self->{'use_threads'} = 0;
        if($Config{useithreads}) {
            $self->{'use_threads'} = 1;
        }
    }
    if($self->{'use_threads'}) {
        eval {
            require threads;
            require Thread::Queue;
        };
        if($@) {
            $self->{'use_threads'} = 0;
            $self->{'logger'}->debug('error initializing threads: '.$@) if defined $self->{'logger'};
        } else {
            $self->_start_worker;
        }
    }

    # initialize peer keys
    $self->{'peer_by_key'} = {};
    $self->{'peer_by_addr'} = {};
    for my $peer (@{$self->{'peers'}}) {
        $self->{'peer_by_key'}->{$peer->peer_key}   = $peer;
        $self->{'peer_by_addr'}->{$peer->peer_addr} = $peer;
    }

    $self->{'name'} = 'multiple connector' unless defined $self->{'name'};
    $self->{'logger'}->debug('initialized Monitoring::Livestatus::MULTI '.($self->{'use_threads'} ? 'with' : 'without' ).' threads') if $self->{'verbose'};

    return $self;
}


########################################

=head1 METHODS

=head2 do

See L<Monitoring::Livestatus> for more information.

=cut

sub do {
    my $self  = shift;
    my $opts  = $self->_lowercase_and_verify_options($_[1]);
    my $t0    = [gettimeofday];

    $self->_do_on_peers("do", $opts->{'backends'}, @_);
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for do('.$_[0].') in total') if $self->{'verbose'};
    return 1;
}


########################################

=head2 selectall_arrayref

See L<Monitoring::Livestatus> for more information.

=cut

sub selectall_arrayref {
    my $self  = shift;
    my $opts  = $self->_lowercase_and_verify_options($_[1]);
    my $t0    = [gettimeofday];

    $self->_log_statement($_[0], $opts, 0) if $self->{'verbose'};

    my $return  = $self->_merge_answer($self->_do_on_peers("selectall_arrayref", $opts->{'backends'}, @_));
    my $elapsed = tv_interval ( $t0 );
    if($self->{'verbose'}) {
        my $total_results = 0;
        $total_results    = scalar @{$return} if defined $return;
        $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectall_arrayref() in total, results: '.$total_results);
    }

    return $return;
}


########################################

=head2 selectall_hashref

See L<Monitoring::Livestatus> for more information.

=cut

sub selectall_hashref {
    my $self  = shift;
    my $opts  = $self->_lowercase_and_verify_options($_[2]);
    my $t0    = [gettimeofday];

    my $return  = $self->_merge_answer($self->_do_on_peers("selectall_hashref", $opts->{'backends'}, @_));
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectall_hashref() in total') if $self->{'verbose'};

    return $return;
}


########################################

=head2 selectcol_arrayref

See L<Monitoring::Livestatus> for more information.

=cut

sub selectcol_arrayref {
    my $self  = shift;
    my $opts  = $self->_lowercase_and_verify_options($_[1]);
    my $t0    = [gettimeofday];

    my $return  = $self->_merge_answer($self->_do_on_peers("selectcol_arrayref", $opts->{'backends'}, @_));
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectcol_arrayref() in total') if $self->{'verbose'};

    return $return;
}


########################################

=head2 selectrow_array

See L<Monitoring::Livestatus> for more information.

=cut

sub selectrow_array {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $self->_lowercase_and_verify_options($_[1]);
    my $t0        = [gettimeofday];
    my @return;

    if((defined $opts->{'sum'} and $opts->{'sum'} == 1) or (!defined $opts->{'sum'} and $statement =~ m/^Stats:/mx)) {
        @return = @{$self->_sum_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backends'}, @_))};
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_arrayref without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backends'}, @_));
        @return = @{$rows} if defined $rows;
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_array() in total') if $self->{'verbose'};

    return @return;
}


########################################

=head2 selectrow_arrayref

See L<Monitoring::Livestatus> for more information.

=cut

sub selectrow_arrayref {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $self->_lowercase_and_verify_options($_[1]);
    my $t0        = [gettimeofday];
    my $return;

    if((defined $opts->{'sum'} and $opts->{'sum'} == 1) or (!defined $opts->{'sum'} and $statement =~ m/^Stats:/mx)) {
        $return = $self->_sum_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backends'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_arrayref without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backends'}, @_));
        $return = $rows->[0] if defined $rows->[0];
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_arrayref() in total') if $self->{'verbose'};

    return $return;
}


########################################

=head2 selectrow_hashref

See L<Monitoring::Livestatus> for more information.

=cut

sub selectrow_hashref {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $self->_lowercase_and_verify_options($_[1]);

    my $t0 = [gettimeofday];

    my $return;

    if((defined $opts->{'sum'} and $opts->{'sum'} == 1) or (!defined $opts->{'sum'} and $statement =~ m/^Stats:/mx)) {
        $return = $self->_sum_answer($self->_do_on_peers("selectrow_hashref", $opts->{'backends'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_hashref without Stats on multi backend will not work as expected!");
        }
        $return = $self->_merge_answer($self->_do_on_peers("selectrow_hashref", $opts->{'backends'}, @_));
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_hashref() in total') if $self->{'verbose'};

    return $return;
}


########################################

=head2 selectscalar_value

See L<Monitoring::Livestatus> for more information.

=cut

sub selectscalar_value {
    my $self  = shift;
    my $statement = $_[0];
    my $opts      = $self->_lowercase_and_verify_options($_[1]);

    my $t0 = [gettimeofday];

    my $return;

    if((defined $opts->{'sum'} and $opts->{'sum'} == 1) or (!defined $opts->{'sum'} and $statement =~ m/^Stats:/mx)) {
        return $self->_sum_answer($self->_do_on_peers("selectscalar_value", $opts->{'backends'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("selectscalar_value without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("selectscalar_value", $opts->{'backends'}, @_));

        $return = $rows->[0] if defined $rows->[0];
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectscalar_value() in total') if $self->{'verbose'};

    return $return;
}


########################################

=head2 errors_are_fatal

See L<Monitoring::Livestatus> for more information.

=cut

sub errors_are_fatal {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('errors_are_fatal', $value);
}


########################################

=head2 warnings

See L<Monitoring::Livestatus> for more information.

=cut

sub warnings {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('warnings', $value);
}


########################################

=head2 verbose

See L<Monitoring::Livestatus> for more information.

=cut

sub verbose {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('verbose', $value);
}


########################################

=head2 peer_addr

See L<Monitoring::Livestatus> for more information.

=cut

sub peer_addr {
    my $self  = shift;

    my @addrs;
    for my $peer (@{$self->{'peers'}}) {
        push @addrs, $peer->peer_addr;
    }

    return wantarray ? @addrs : undef;
}


########################################

=head2 peer_name

See L<Monitoring::Livestatus> for more information.

=cut

sub peer_name {
    my $self  = shift;

    my @names;
    for my $peer (@{$self->{'peers'}}) {
        push @names, $peer->peer_name;
    }

    return wantarray ? @names : $self->{'name'};
}


########################################

=head2 peer_key

See L<Monitoring::Livestatus> for more information.

=cut

sub peer_key {
    my $self  = shift;

    my @keys;
    for my $peer (@{$self->{'peers'}}) {
        push @keys, $peer->peer_key;
    }

    return wantarray ? @keys : $self->{'key'};
}


########################################

=head2 disable

 $ml->disable()

disables this connection, returns the last state.

=cut
sub disable {
    my $self     = shift;
    my $peer_key = shift;
    if(!defined $peer_key) {
        for my $peer (@{$self->{'peers'}}) {
            $peer->disable();
        }
        return 1;
    } else {
        my $peer     = $self->_get_peer_by_key($peer_key);
        my $prev     = $peer->{'disabled'};
        $peer->{'disabled'} = 1;
        return $prev;
    }
}


########################################

=head2 enable

 $ml->enable()

enables this connection, returns the last state.

=cut
sub enable {
    my $self     = shift;
    my $peer_key = shift;
    if(!defined $peer_key) {
        for my $peer (@{$self->{'peers'}}) {
            $peer->enable();
        }
        return 1;
    } else {
        my $peer     = $self->_get_peer_by_key($peer_key);
        my $prev     = $peer->{'disabled'};
        $peer->{'disabled'} = 0;
        return $prev;
    }
}

########################################
# INTERNAL SUBS
########################################

sub _change_setting {
    my $self  = shift;
    my $key   = shift;
    my $value = shift;
    my $old   = $self->{$key};

    # set new value
    if(defined $value) {
        $self->{$key} = $value;
        for my $peer (@{$self->{'peers'}}) {
            $peer->{$key} = $value;
        }

        # restart workers
        if($self->{'use_threads'}) {
            _stop_worker();
            $self->_start_worker();
        }
    }

    return $old;
}


########################################
sub _start_worker {
    my $self = shift;

    # create job transports
    $self->{'WorkQueue'}   = Thread::Queue->new;
    $self->{'WorkResults'} = Thread::Queue->new;

    # set signal handler before thread is started
    # otherwise they would be killed when started
    # and stopped immediately after start
    $SIG{'USR1'} = sub { threads->exit(); };

    # start worker threads
    our %threads;
    my $threadcount = scalar @{$self->{'peers'}};
    for(my $x = 0; $x < $threadcount; $x++) {
        $self->{'threads'}->[$x] = threads->new(\&_worker_thread, $self->{'peers'}, $self->{'WorkQueue'}, $self->{'WorkResults'}, $self->{'logger'});
    }

    # restore sig handler as it was only for the threads
    $SIG{'USR1'} = 'DEFAULT';
    return;
}


########################################
sub _stop_worker {
    # try to kill our threads safely
    eval {
        for my $thr (threads->list()) {
            $thr->kill('USR1')->detach();
        }
    };
    return;
}


########################################
sub _worker_thread {
    local $SIG{'USR1'} = sub { threads->exit(); };

    my $peers       = shift;
    my $workQueue   = shift;
    my $workResults = shift;
    my $logger      = shift;

    while (my $job = $workQueue->dequeue) {
        my $erg;
        eval {
            $erg = _do_wrapper($peers->[$job->{'peer'}], $job->{'sub'}, $logger, @{$job->{'opts'}});
        };
        if($@) {
            warn("Error in Thread ".$job->{'peer'}." :".$@);
            $job->{'logger'}->error("Error in Thread ".$job->{'peer'}." :".$@) if defined $job->{'logger'};
        };
        $workResults->enqueue({ peer => $job->{'peer'}, result => $erg });
    }
    return;
}


########################################
sub _do_wrapper {
    my $peer   = shift;
    my $sub    = shift;
    my $logger = shift;
    my @opts   = @_;

    my $t0 = [gettimeofday];

    my $data = $peer->$sub(@opts);

    my $elapsed = tv_interval ( $t0 );
    $logger->debug(sprintf('%.4f', $elapsed).' sec for fetching data on '.$peer->peer_name.' ('.$peer->peer_addr.')') if defined $logger;

    $Monitoring::Livestatus::ErrorCode    = 0 unless defined $Monitoring::Livestatus::ErrorCode;
    $Monitoring::Livestatus::ErrorMessage = '' unless defined $Monitoring::Livestatus::ErrorMessage;
    my $return = {
            'msg'  => $Monitoring::Livestatus::ErrorMessage,
            'code' => $Monitoring::Livestatus::ErrorCode,
            'data' => $data,
    };
    return $return;
}


########################################
sub _do_on_peers {
    my $self        = shift;
    my $sub         = shift;
    my $backends    = shift;
    my @opts        = @_;
    my $statement   = $opts[0];
    my $use_threads = $self->{'use_threads'};
    my $t0          = [gettimeofday];

    my $return;
    my %codes;
    my %messages;
    my $query_options;
    if($sub eq 'selectall_hashref') {
        $query_options = $self->_lowercase_and_verify_options($opts[2]);
    } else {
        $query_options = $self->_lowercase_and_verify_options($opts[1]);
    }

    # which peers affected?
    my @peers;
    if(defined $backends) {
        my @backends;
        if(ref $backends eq '') {
            push @backends, $backends;
        }
        elsif(ref $backends eq 'ARRAY') {
            @backends = @{$backends};
        } else {
            croak("unsupported type for backend: ".ref($backends));
        }

        for my $key (@backends) {
            my $backend = $self->_get_peer_by_key($key);
            push @peers, $backend unless $backend->{'disabled'};
        }
    } else {
        # use all backends
        @peers = @{$self->{'peers'}};
    }

    # its faster without threads for only one peer
    if(scalar @peers <= 1) { $use_threads = 0; }

    # if we have limits set, we cannot use threads
    if(defined $query_options->{'limit_start'}) { $use_threads = 0; }

    if($use_threads) {
        # use the threaded variant
        $self->{'logger'}->debug('using threads') if $self->{'verbose'};

        my $peers_to_use;
        for my $peer (@peers) {
            if($peer->{'disabled'}) {
                # dont send any query
            }
            elsif($peer->marked_bad) {
                warn($peer->peer_name.' ('.$peer->peer_key.') is marked bad') if $self->{'verbose'};
            }
            else {
                $peers_to_use->{$peer->peer_key} = 1;
            }
        }
        my $x = 0;
        for my $peer (@{$self->{'peers'}}) {
            if(defined $peers_to_use->{$peer->peer_key}) {
                my $job = {
                        'peer'   => $x,
                        'sub'    => $sub,
                        'opts'   => \@opts,
                };
                $self->{'WorkQueue'}->enqueue($job);
            }
            $x++;
        }

        for(my $x = 0; $x < scalar keys %{$peers_to_use}; $x++) {
            my $result = $self->{'WorkResults'}->dequeue;
            my $peer   = $self->{'peers'}->[$result->{'peer'}];
            if(defined $result->{'result'}) {
                push @{$codes{$result->{'result'}->{'code'}}}, { 'peer' => $peer->peer_key, 'msg' => $result->{'result'}->{'msg'} };
                $return->{$peer->peer_key} = $result->{'result'}->{'data'};
            } else {
                warn("undefined result for: $statement");
            }
        }
    } else {
        $self->{'logger'}->debug('not using threads') if $self->{'verbose'};
        for my $peer (@peers) {
            if($peer->{'disabled'}) {
                # dont send any query
            }
            elsif($peer->marked_bad) {
                warn($peer->peer_name.' ('.$peer->peer_key.') is marked bad') if $self->{'verbose'};
            } else {
                my $erg = _do_wrapper($peer, $sub, $self->{'logger'}, @opts);
                $return->{$peer->peer_key} = $erg->{'data'};
                push @{$codes{$erg->{'code'}}}, { 'peer' => $peer, 'msg' => $erg->{'msg'} };

                # compute limits
                if(defined $query_options->{'limit_length'} and $peer->{'meta_data'}->{'result_count'}) {
                    last;
                }
                # set a new start if we had rows already
                if(defined $query_options->{'limit_start'}) {
                    $query_options->{'limit_start'} = $query_options->{'limit_start'} - $peer->{'meta_data'}->{'row_count'};
                }
            }
        }
    }


    # check if we different result stati
    undef $Monitoring::Livestatus::ErrorMessage;
    $Monitoring::Livestatus::ErrorCode = 0;
    my @codes = sort keys %codes;
    if(scalar @codes > 1) {
        # got different results for our backends
        if($self->{'verbose'}) {
            $self->{'logger'}->warn("got different result stati: ".Dumper(\%codes));
        }
    } else {
        # got same result codes for all backend
    }

    my $failed = 0;
    my $code = $codes[0];
    if(defined $code and $code >= 300) {
        $failed = 1;
    }

    if($failed) {
        my $msg  = $codes{$code}->[0]->{'msg'};
        $self->{'logger'}->debug("same: $code -> $msg") if $self->{'verbose'};
        $Monitoring::Livestatus::ErrorMessage = $msg;
        $Monitoring::Livestatus::ErrorCode    = $code;
        if($self->{'errors_are_fatal'}) {
            croak("ERROR ".$code." - ".$Monitoring::Livestatus::ErrorMessage." in query:\n'".$statement."'\n");
        }
        return;
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for fetching all data') if $self->{'verbose'};

    # deep copy result?
    if($use_threads
       and (
            (defined $query_options->{'deepcopy'} and $query_options->{'deepcopy'} == 1)
            or
            (defined $self->{'deepcopy'}          and $self->{'deepcopy'} == 1)
        )
       ) {
        # result has to be cloned to avoid "Invalid value for shared scalar" error

        $return = $self->_clone($return, $self->{'logger'});
    }

    return($return);
}


########################################
sub _merge_answer {
    my $self   = shift;
    my $data   = shift;
    my $return;

    my $t0 = [gettimeofday];

    # iterate over original peers to retain order
    for my $peer (@{$self->{'peers'}}) {
        my $key = $peer->peer_key;
        next if !defined $data->{$key};

        if(ref $data->{$key} eq 'ARRAY') {
            $return = [] unless defined $return;
            $return = [ @{$return}, @{$data->{$key}} ];
        } elsif(ref $data->{$key} eq 'HASH') {
            $return = {} unless defined $return;
            $return = { %{$return}, %{$data->{$key}} };
        } else {
            push @{$return}, $data->{$key};
        }
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for merging data') if $self->{'verbose'};

    return($return);
}


########################################
sub _sum_answer {
    my $self   = shift;
    my $data   = shift;
    my $return;
    my $t0 = [gettimeofday];
    for my $peername (keys %{$data}) {
        if(ref $data->{$peername} eq 'HASH') {
            for my $key (keys %{$data->{$peername}}) {
                if(!defined $return->{$key}) {
                    $return->{$key} = $data->{$peername}->{$key};
                } elsif(looks_like_number($data->{$peername}->{$key})) {
                    $return->{$key} += $data->{$peername}->{$key};
                }
            }
        }
        elsif(ref $data->{$peername} eq 'ARRAY') {
            my $x = 0;
            for my $val (@{$data->{$peername}}) {
                if(!defined $return->[$x]) {
                    $return->[$x] = $data->{$peername}->[$x];
                } else {
                    $return->[$x] += $data->{$peername}->[$x];
                }
                $x++;
            }
        } elsif(defined $data->{$peername}) {
            $return = 0 unless defined $return;
            next unless defined $data->{$peername};
            $return += $data->{$peername};
        }
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for summarizing data') if $self->{'verbose'};

    return $return;
}


########################################
sub _clone {
    my $self   = shift;
    my $data   = shift;
    my $logger = shift;
    my $t0     = [gettimeofday];

    my $return;
    if(ref $data eq '') {
        $return = $data;
    }
    elsif(ref $data eq 'ARRAY') {
        $return = [];
        for my $dat (@{$data}) {
            push @{$return}, $self->_clone($dat);
        }
    }
    elsif(ref $data eq 'HASH') {
        $return = {};
        for my $key (keys %{$data}) {
            $return->{$key} = $self->_clone($data->{$key});
        }
    }
    else {
        croak("cant clone: ".(ref $data));
    }

    my $elapsed = tv_interval ( $t0 );
    $logger->debug(sprintf('%.4f', $elapsed).' sec for cloning data') if defined $logger;

    return $return;
}


########################################
sub _get_peer_by_key {
    my $self = shift;
    my $key  = shift;

    return unless defined $key;
    return unless defined $self->{'peer_by_key'}->{$key};

    return $self->{'peer_by_key'}->{$key};
}


########################################
sub _get_peer_by_addr {
    my $self = shift;
    my $addr = shift;

    return unless defined $addr;
    return unless defined $self->{'peer_by_addr'}->{$addr};

    return $self->{'peer_by_addr'}->{$addr};
}


########################################

END {
    # try to kill our threads safely
    _stop_worker();
}

########################################

1;

=head1 AUTHOR

Sven Nierlein, E<lt>nierlein@cpan.orgE<gt>

=head1 COPYRIGHT AND LICENSE

Copyright (C) 2009 by Sven Nierlein

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut

__END__
