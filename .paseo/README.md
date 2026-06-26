# .paseo

Repo-side helpers for working on Checkmk with [paseo](https://app.paseo.sh).

## Sandboxing Claude with firejail (opt-in)

Running Claude in a [firejail](https://firejail.wordpress.com/) sandbox is
optional. To enable it, run

```sh
./.paseo/setup-claude-firejail.sh
```

once, restart paseo (it reads the config only at startup), then pick the
**"Claude (firejail)"** provider instead of **"Claude"** when creating a new
workspace.

### Custom whitelist paths

The sandbox masks everything under your home directory that the profile does not
explicitly whitelist. The setup script offers to whitelist `~/.netrc` and your
SSH private keys; to grant Claude any other outside path (a shared virtualenvs
dir, an extra credentials file, …), add lines to
`~/.config/firejail/claude.local`, which firejail includes after the profile so
your edits survive profile updates:

```
# ~/.config/firejail/claude.local
whitelist ${HOME}/.venvs        # writable
whitelist-ro ${HOME}/.netrc     # read-only
```
