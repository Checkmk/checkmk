# shellcheck disable=SC2148
# When a user switches to the site user using "su <site>" instead
# of "su - <site>" the .profile is not loaded. This checks the
# situation and sources the .profile when it has not been executed
# yet.
# The .profile file tries to execute the .bashrc script on it's
# own. This is needed in "su - <site>" mode. But must be prevented
# in the "su <site>" mode. So we define the variable BASHRC here
# and check it in .profile.
BASHRC=1
export BASHRC
if [ -z "${OMD_ROOT:-}" ]; then
    # shellcheck source=/dev/null
    . ~/.profile
    cd ~ || exit
fi
alias cpan='cpan.wrapper'

# pointless unless running interactively
if [ -n "${PS1:-}" ]; then
    PS1='OMD[\u]:\w$ '
    alias ls='ls --color=auto -F'
    alias ll='ls -l'
    alias la='ls -la'

    if [ -f /etc/bash_completion ]; then
        # Load system wide bash completion (if available)
        # shellcheck disable=SC1091
        . /etc/bash_completion

        # Load site specific bash completions
        j="$OMD_ROOT/etc/bash_completion.d"
        if [ -d "$j" ] && [ -r "$j" ] && [ -x "$j" ]; then
            for i in $(LC_ALL=C command ls "$j"); do
                i="$j/$i"
                # shellcheck disable=SC1090
                [ -f "$i" ] && [ -r "$i" ] && . "$i"
            done
            unset i
        fi
        unset j
    fi
fi
