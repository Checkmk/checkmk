# cmk-dev-site

_Easy Install Checkmk_

Scripts to install bleeding edge Checkmk in development context.

**If you are a regular Checkmk customer you probably don't want to use this,
as this tools remove sites without warning.**

## Installation

```
sudo apt install pipx
pipx ensurepath
# check output of this command. you might have to open a fresh terminal!
pipx install cmk-dev-site
```

For updating you can use:

```
pipx upgrade cmk-dev-site
```

With uv, use `uv tool install cmk-dev-site` and `uv tool upgrade cmk-dev-site`
instead.

The commands check PyPI for a newer version at most once a day and print a
warning with the matching upgrade command at the start and the end of a run.
Set `CMK_DEV_SITE_NO_UPDATE_CHECK=1` to turn this off.

## Usage

```
cmk-dev-install-site 2.5 # download package, install, create site for 2.5

# Download and install latest available daily build of 2.5.0
cmk-dev-install 2.5 && cmk-dev-site
# (will fall back to the daily builds of yesterday)

# Download daily build of today and
# setup distributed monitoring with one two sites:
cmk-dev-install 2.5.0-daily && cmk-dev-site -d 1

# Download and install raw edition package
cmk-dev-install --edition=cre 2.5.0-daily

# Install a local .deb file instead of downloading
cmk-dev-install -p ./check-mk-enterprise-2.4.0p9_0.noble_amd64.deb
```

### `cmk-dev-install-site`

Is a shortcut for the more verbose `cmk-dev-install` and `cmk-dev-site`
commands. This way you lose some of the possibilities, but only have to
remember one command. Also prints out the commands that it will execute, so you
can c&p it.

This shortcut does not forward `--omd-configs`, `--show-trial-mode-selection`
or `--ai-assistant`, so opting out of the MCP server, of the usage-data
forwarding or of the trial mode preselection, and turning on the AI assistant
flag (see `cmk-dev-site` below), requires calling `cmk-dev-site` directly.

### `cmk-dev-install`

Will download the requested package of Checkmk and install said package.

You might request a daily build (`cmk-dev-install 2.5.0-daily`),
the latest available daily build (handy if there are no daily builds of today) (`cmk-dev-install 2.5`),
or an officially release Checkmk version (`cmk-dev-install 2.4.0p9`).

Please check the built in help (`cmk-dev-install --help`) for all options!

### `cmk-dev-site`

Will create a site, install the checkmk agent, and add a single host to the site.

`cmk-dev-site` uses [omd
commands](https://docs.checkmk.com/latest/en/omd_basics.html) and the official
[REST-API](https://docs.checkmk.com/latest/en/rest_api.html) to create one or
multiple sites based on the current default omd version (or the version
specified on the command line).

You might use `-d 1` to create a distributed monitoring with one distributed site.

Where the installed version ships the hooks (currently Checkmk 3.0.0+, every
edition except community), the site is created with the MCP server enabled at
`http://localhost/<site>/check_mk/mcp`, and with `MCP_TRACE_FORWARD=on`, which
forwards MCP usage data to Checkmk. Opt out with `--omd-configs MCP_SERVER=off`
or `--omd-configs MCP_TRACE_FORWARD=off`.

Every site is created with trial mode preselected, so Checkmk does not ask on
login whether the site is used as a trial or with an existing license. Pass
`--show-trial-mode-selection` to be asked instead.

Pass `--ai-assistant` to create the central site with Checkmk's
`exp_ai_assistant` experimental flag on, so the AI assistant settings show in
Global settings. This works on Checkmk versions that ship the AI assistant (the
non-free editions of 2.5.0p14 and later, and of 3.0.0 builds from late September
2026 on); on other versions the option does nothing. To start the AI assistant
service, make sure the global setting "Enable the AI assistant" is on, save it,
and activate changes. On Checkmk versions where that setting is on by default
(current 3.0.0 builds), the activation at the end of a distributed run (`-d N`)
already starts the service on the central site.

Please check the built in help (`cmk-dev-site --help`) for all options!

### Cleanup

Currently there is no public available tool to completely cleanup sites and
packages create with the presented tools. If you are a Checkmk developer you
might make use of the internal tool `omd-hauweg`, otherwise you have to
manually remove the sites using `omd rm`.
For uninstall packages that are no longer in use you can use `omd cleanup`,
or you might fall back to use `apt purge`.

## Contributing

If you'd like to make contributions to the tool, check out our
[development documentation](https://github.com/Checkmk/cmk-dev-site/blob/main/DEVELOPMENT.md).
Here you'll see steps on how to setup your environment for local development.
