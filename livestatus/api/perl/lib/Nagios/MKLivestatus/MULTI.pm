package Nagios::MKLivestatus::MULTI;

use 5.000000;
use strict;
use warnings;
use Carp;
use Data::Dumper;
use Config;
use Time::HiRes qw( gettimeofday tv_interval );
use Nagios::MKLivestatus;
use base "Nagios::MKLivestatus";

=head1 NAME

Nagios::MKLivestatus::MULTI - connector with multiple peers

=head1 SYNOPSIS

    use Nagios::MKLivestatus;
    my $nl = Nagios::MKLivestatus::MULTI->new( qw{nagioshost1:9999 nagioshost2:9999 /var/spool/nagios/live.socket} );
    my $hosts = $nl->selectall_arrayref("GET hosts");

=head1 CONSTRUCTOR

=head2 new ( [ARGS] )

Creates an C<Nagios::MKLivestatus::MULTI> object. C<new> takes at least the server.
Arguments are the same as in L<Nagios::MKLivestatus>.

=cut

sub new {
    my $class = shift;
    unshift(@_, "peer") if scalar @_ == 1;
    my(%options) = @_;

    $options{'backend'} = $class;
    my $self = Nagios::MKLivestatus->new(%options);
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
                push @{$peers}, new Nagios::MKLivestatus::UNIX(%peer_options);
            }
            elsif($peer->{'type'} eq 'INET') {
                push @{$peers}, new Nagios::MKLivestatus::INET(%peer_options);
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
        };
    }
    if($self->{'use_threads'}) {
        require threads;
        require Thread::Queue;

        $self->_start_worker;
    }

    # initialize peer keys
    $self->{'peer_by_key'} = {};
    for my $peer (@{$self->{'peers'}}) {
        $self->{'peer_by_key'}->{$peer->peer_key} = $peer;
    }

    $self->{'name'} = 'multiple connector' unless defined $self->{'name'};
    $self->{'logger'}->debug('initialized Nagios::MKLivestatus::MULTI '.($self->{'use_threads'} ? 'with' : 'without' ).' threads') if defined $self->{'logger'};

    return $self;
}


########################################

=head1 METHODS

=head2 do

See L<Nagios::MKLivestatus> for more information.

=cut

sub do {
    my $self  = shift;
    my $opts  = $_[1];
    my $t0    = [gettimeofday];

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    $self->_do_on_peers("do", $opts->{'backend'}, @_);
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for do('.$_[0].') in total') if defined $self->{'logger'};
    return 1;
}

########################################

=head2 selectall_arrayref

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectall_arrayref {
    my $self  = shift;
    my $opts  = $_[1];
    my $t0    = [gettimeofday];

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    my $return  = $self->_merge_answer($self->_do_on_peers("selectall_arrayref", $opts->{'backend'}, @_));
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectall_arrayref() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 selectall_hashref

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectall_hashref {
    my $self  = shift;
    my $opts  = $_[2];
    my $t0    = [gettimeofday];

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    my $return  = $self->_merge_answer($self->_do_on_peers("selectall_hashref", $opts->{'backend'}, @_));
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectall_hashref() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 selectcol_arrayref

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectcol_arrayref {
    my $self  = shift;
    my $opts  = $_[1];
    my $t0    = [gettimeofday];

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    my $return  = $self->_merge_answer($self->_do_on_peers("selectcol_arrayref", $opts->{'backend'}, @_));
    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectcol_arrayref() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 selectrow_array

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectrow_array {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $_[1];
    my $t0        = [gettimeofday];
    my @return;

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    if(defined $opts->{'sum'} or $statement =~ m/^Stats:/mx) {
        @return = @{$self->_sum_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backend'}, @_))};
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_arrayref without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backend'}, @_));
        @return = @{$rows} if defined $rows;
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_array() in total') if defined $self->{'logger'};

    return @return;
}

########################################

=head2 selectrow_arrayref

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectrow_arrayref {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $_[1];
    my $t0        = [gettimeofday];
    my $return;

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    if(defined $opts->{'sum'} or $statement =~ m/^Stats:/mx) {
        $return = $self->_sum_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backend'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_arrayref without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("selectrow_arrayref", $opts->{'backend'}, @_));
        $return = $rows->[0] if defined $rows->[0];
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_arrayref() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 selectrow_hashref

See L<Nagios::MKLivestatus> for more information.

=cut

sub selectrow_hashref {
    my $self      = shift;
    my $statement = $_[0];
    my $opts      = $_[1];

    my $t0 = [gettimeofday];

    my $return;

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    if(defined $opts->{'sum'} or $statement =~ m/^Stats:/mx) {
        $return = $self->_sum_answer($self->_do_on_peers("selectrow_hashref", $opts->{'backend'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("selectrow_hashref without Stats on multi backend will not work as expected!");
        }
        $return = $self->_merge_answer($self->_do_on_peers("selectrow_hashref", $opts->{'backend'}, @_));
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for selectrow_hashref() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 select_scalar_value

See L<Nagios::MKLivestatus> for more information.

=cut

sub select_scalar_value {
    my $self  = shift;
    my $statement = $_[0];
    my $opts      = $_[1];

    my $t0 = [gettimeofday];

    # make opt hash keys lowercase
    %{$opts} = map { lc $_ => $opts->{$_} } keys %{$opts};

    my $return;

    if(defined $opts->{'sum'} or $statement =~ m/^Stats:/mx) {
        return $self->_sum_answer($self->_do_on_peers("select_scalar_value", $opts->{'backend'}, @_));
    } else {
        if($self->{'warnings'}) {
            carp("select_scalar_value without Stats on multi backend will not work as expected!");
        }
        my $rows = $self->_merge_answer($self->_do_on_peers("select_scalar_value", $opts->{'backend'}, @_));

        $return = $rows->[0] if defined $rows->[0];
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for select_scalar_value() in total') if defined $self->{'logger'};

    return $return;
}

########################################

=head2 errors_are_fatal

See L<Nagios::MKLivestatus> for more information.

=cut

sub errors_are_fatal {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('errors_are_fatal', $value);
}

########################################

=head2 warnings

See L<Nagios::MKLivestatus> for more information.

=cut

sub warnings {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('warnings', $value);
}

########################################

=head2 verbose

See L<Nagios::MKLivestatus> for more information.

=cut

sub verbose {
    my $self  = shift;
    my $value = shift;
    return $self->_change_setting('verbose', $value);
}


########################################

=head2 peer_addr

See L<Nagios::MKLivestatus> for more information.

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

See L<Nagios::MKLivestatus> for more information.

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

See L<Nagios::MKLivestatus> for more information.

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

    $Nagios::MKLivestatus::ErrorCode    = 0 unless defined $Nagios::MKLivestatus::ErrorCode;
    $Nagios::MKLivestatus::ErrorMessage = '' unless defined $Nagios::MKLivestatus::ErrorMessage;
    my $return = {
            'msg'  => $Nagios::MKLivestatus::ErrorMessage,
            'code' => $Nagios::MKLivestatus::ErrorCode,
            'data' => $data,
    };
    return $return;
}

########################################
sub _do_on_peers {
    my $self      = shift;
    my $sub       = shift;
    my $backends  = shift;
    my @opts      = @_;
    my $statement = $opts[0];

    my $t0 = [gettimeofday];

    my $return;
    my %codes;
    my %messages;
    my $use_threads = $self->{'use_threads'};

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

        for my $back (@backends) {
            push @peers, $self->_get_peer_by_key($back);
        }
    } else {
        # use all backends
        @peers = @{$self->{'peers'}};
    }

    # its faster without threads for only one peer
    if(scalar @peers <= 1) { $use_threads = 0; }

    if($use_threads) {
        # use the threaded variant
        print("using threads\n") if $self->{'verbose'};

        my $x = 0;
        for my $peer (@peers) {
            my $job = {
                    'peer'   => $x,
                    'sub'    => $sub,
                    'opts'   => \@opts,
            };
            $self->{'WorkQueue'}->enqueue($job);
            $x++;
        }

        for(my $x = 0; $x < scalar @peers; $x++) {
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
        print("not using threads\n") if $self->{'verbose'};
        for my $peer (@peers) {
            if($peer->marked_bad) {
                warn($peer->peer_name.' ('.$peer->peer_key.') is marked bad') if $self->{'verbose'};
            } else {
                my $erg = _do_wrapper($peer, $sub, $self->{'logger'}, @opts);
                $return->{$peer->peer_key} = $erg->{'data'};
                push @{$codes{$erg->{'code'}}}, { 'peer' => $peer, 'msg' => $erg->{'msg'} };
            }
        }
    }


    # check if we different result stati
    undef $Nagios::MKLivestatus::ErrorMessage;
    $Nagios::MKLivestatus::ErrorCode = 0;
    my @codes = keys %codes;
    if(scalar @codes > 1) {
        # got different results for our backends
        print "got different result stati: ".Dumper(\%codes) if $self->{'verbose'};
    } else {
        # got same result codes for all backend
        my $code = $codes[0];
        if($code >= 300) {
            my $msg  = $codes{$code}->[0]->{'msg'};
            print "same: $code -> $msg\n" if $self->{'verbose'};
            $Nagios::MKLivestatus::ErrorMessage = $msg;
            $Nagios::MKLivestatus::ErrorCode    = $code;
            if($self->{'errors_are_fatal'}) {
                croak("ERROR ".$code." - ".$Nagios::MKLivestatus::ErrorMessage." in query:\n'".$statement."'\n");
            }
            return;
        }
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for fetching all data') if defined $self->{'logger'};

    if($use_threads) {
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
    for my $key (keys %{$data}) {
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
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for merging data') if defined $self->{'logger'};

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
                } else {
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
        }
    }

    my $elapsed = tv_interval ( $t0 );
    $self->{'logger'}->debug(sprintf('%.4f', $elapsed).' sec for summarizing data') if defined $self->{'logger'};

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
