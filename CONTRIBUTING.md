# Contributing to Checkmk

Thanks for your interest to contribute to [Checkmk on Github](https://github.com/tribe29/checkmk)!

Here are some ways you can help out:

* Bug fixes
* Feature enhancements
* New plugins

Here are the links to major sections of this document:

* [Contributing Code](#contributing-code)
* [How to prepare for contributing](#how-to-prepare-for-contributing)
* [How to change Checkmk](#how-to-change-checkmk)
* [How to execute tests](#how-to-execute-tests)
* [Style Guide](#style-guide)

If you have questions, please create a post at the [Checkmk Forum](https://forum.checkmk.com). For bug reports, please send an e-mail to feedback@checkmk.com

If you would like to make a major change to Checkmk, please create a new topic
under the [Product Ideas category](https://forum.checkmk.com/c/product-ideas/19)
in the Checkmk Forum so we can talk about what you want to do. Somebody else may
already be working on it, or there are certain topics you should know before
implementing the change.

We love to work with community contributors and want to make sure contributions
and time investments are as effective as possible. That's why it is important
to us to discuss major changes you might be planning in order to jointly agree
on the best solution approach to the problem at hand. This preempts potential
issues during the code reviews of pull requests. Code reviews can take time and
we're trying our best to address your PRs as soon as we can.

Unfortunately, it can also happen that we cannot accommodate what you want to
work on due to the set priorities. For example, currently we might be unable to
review changes and suggestions that will affect the core functionalities of
Checkmk due to other major changes in the codebase.

## Contributing code

In general, we follow the standard GitHub workflow which roughly works like
this:

 1. **Fork** the repository on GitHub
 2. **Clone** the forked repository to your own machine
 3. **Commit** changes to your own feature branch
 4. **Push** your work back up to your forked repository
 5. Submit a **Pull request** (PR) so that we can review your changes

 ⚠ Please reply when asked for more information or to update your PR
in case in didn't meet the requirements (e.g. failed checks).
If there's no response from the author for at least 14 days, the PR will be closed.

If it’s your first time to contribute to an open source project, we recommend reading
[this guide](https://opensource.guide/how-to-contribute/). You may also want to
try the [GitHub Hello World tutorial](https://guides.github.com/activities/hello-world/).

## How to prepare for contributing

We are developing Checkmk on **Ubuntu Linux** systems. It's not a hard requirement, but
most helper scripts are optimized for this, so we highly recommend it for best
experience.

To set up the development environment do the following:

1. [Fork the repository and clone to your computer](https://help.github.com/en/github/getting-started-with-github/fork-a-repo)

    Then change to the just created project directory.

    ```console
    cd checkmk
    ```

2. Install development dependencies

    Before you can start working on Checkmk, you will have to install some
    additional software, like tools for development and testing. Execute this in
    the project directory:

    ```console
    $ make setup
    ```

    > This is optimized for Ubuntu, but you may also get all the required programs
    > on other platforms.

    After the dependencies have been installed, you could execute the shipped
    tests to ensure everything is working fine before start making changes to
    Checkmk.
    If you like to do this, please have a look at the [How to execute tests?](#how-to-execute-tests)
    chapter.

3. Install pre-commit checks

    In order to keep your commits to our standard we provide a [pre-commit](https://pre-commit.com/)
    configuration and some custom made checking scripts. You can install it like this:

    > Warning: Python3 is required for pre-commit! Installing it with Python 2 will break
    > your environment and leave you unable to use pip due to a backports module clash!

    ```console
    $ pip3 install pre-commit
    ```

    After successful installation, hook it up to your git-repository by issuing
    the following command inside your git repository:

    ```console
    $ pre-commit install --allow-missing-config
    ```

    The `--allow-missing-config` parameter is needed so that branches of older versions of Checkmk which don't
    support this feature and are missing the configuration file won't throw errors.

    Afterwards your commits will automatically be checked for conformity by `pre-commit`. If you know a
    check (like mypy for example) got something wrong and you don't want to fix it right away you can skip
    execution of the checkers with `git commit -n`. Please don't push unchecked changes as this will
    introduce delays and additional work.

    Additional helpers can be found in `scripts/`. One notable one is `scripts/check-current-commit`
    which checks your commit *after* it has been made. You can then fix errors and amend or squash
    your commit. You can also use this script in a rebase like such:

    ```console
    $ git rebase --exec scripts/check-current-commit
    ```

    This will rebase your current changes and check each commit for errors. After fixing them you can
    then continue rebasing.

Once done, you are ready for the next chapter.

## How to change Checkmk

1. Create your feature branch

    The number one rule is to *put each piece of work on its own branch*. Please note that in
    general, we only accept changes which are based on the *master* branch. There is one (rare)
    exception, namely bugfixes which *only* affect older branches. So lets start like this:

    ```console
    $ git checkout master
    $ git checkout -b my-feature-branch
    ```

    The first command ensures you start with the master branch. The second command
    created the branch `my-feature-branch`. Pick some descriptive name you can remember later.

    Let's check if everything worked fine:

    ```console
    $ git status
    On branch my-feature-branch
    (...)
    ```

2. Start developing and create one or multiple commits.

    **Important**: Do one thing in one commit, e.g. don't mix code reorganization and
    changes of the moved lines. Separate this in two commits.

    Make sure that you commit in logical blocks and write [good commit messages](#style-guide-commit-messages).

    If you have finished your work, it's a good time to [execute the tests locally](#how-to-execute-tests) to ensure you did not break anything.

    Once you are done with the commits and tests in your feature branch you could push them to your own GitHub fork like this.

    ```console
    $ git push -u origin my-feature-branch
    ```

    In the output of this command you will see a URL which you can open to create a pull request from your feature branch.

3. Submit a pull request (PR)

    On GitHub in your browser, submit a pull request from your `my-feature-branch` to the official Checkmk branch you forked from.

    The Travis CI bot will start testing your commits for issues. In case there are
    issues, it will send you a mail and ask you to [fix the issues](#help-i-need-to-change-my-commits).

### Help: I have a conflict

If you are working on a change in a file while the same file changes in the
official repository, this will produce a merge conflict once you try to
upstream your change.

To avoid that, it is recommended to rebase your own changes often on top of the
current upstream branch.

To be able to do this, you need to prepare your project directory once with
this command:

```console
$ git remote add upstream https://github.com/tribe29/checkmk.git
```

From now, you can always update your feature branches with this command:

```console
$ git pull --rebase upstream master
```

> Using rebase instead of merge gives us a clean git history.

### Help: I need to change my commits

In case Travis notifies you about issues or the reviewer asks you to change
your code, you will have to rework your commits. Be sure, we don't want to
upset you :-).

There are several ways to update your changes in Git. We want to have as clean
as possible commits, so the best is to apply the changes in a new commit and
then meld them together with the previous commit.

This article on [how to amend a commit](https://www.burntfen.com/2015-10-30/how-to-amend-a-commit-on-a-github-pull-request) may help you.

## How to execute tests

The public repository of [Checkmk](https://github.com/tribe29/checkmk) is
integrated with Travis CI. Each time a Pull request is submitted, Travis will
have a look at the changes.

**⚠ Important:** We only review PRs that are confirmed to be OK by Travis.
If a check failed, please fix it and update the PR.
PRs will be closed if the author didn't respond for at least 14 days.

It is recommended to run all tests locally before submitting a PR. If you want
to execute the full test suite, you can do this by executing these commands in
the project base directory:

```console
$ make -C tests test-pylint
$ make -C tests test-bandit
$ make -C tests test-unit
$ make -C tests test-format-python
$ make -C tests test-mypy-raw
```

Some of these commands take several minutes, for example the command
`test-format-python` because it tests the formatting of the whole code base.
Normally you only change a small set of files in your commits. If you execute
`black [filename]` to format the changed code, this should be enough and you
don't need to execute the formatting test at all.

> We highly recommend to integrate black, isort, pylint and mypy into the editor you
> work with. Most editors will notify you about issues in the moment you edit
> the code.

You could also push your changed to your forked repository and wait for Travis
to execute the tests for you, but that takes several minutes for each try.

## Style guide

## Guidelines for coding check plug-ins

Respect the [Guidelines for coding check plug-ins](https://docs.checkmk.com/master/en/dev_guidelines.html).

## Commit messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* The first line is a short title (limit to 72 characters or less)
* Reference issues and pull requests liberally after the first line
* Write [good commit messages](https://chris.beams.io/posts/git-commit/)

## Python

The guidelines listed here are binding for the development at Checkmk in
Python.

This list is intended to grow in practice and does not claim to be exhaustive.

First orientate yourself on the existing code. If it doesn't fit these
guidelines at all, it might be better to first orientate yourself on the
existing code and adapt the code to these guidelines separately from any
content changes.

[Zen of Python](https://www.python.org/dev/peps/pep-0020/).

Checkmk is mostly written in Python. At the moment the most of the code base is
using Python 3.9.

Only rely on non-standard modules that are mentioned in the `Pipfile`.
<!--- TODO: How to add new modules? -->

### Agent plugins: Supported Python versions

The agent plugins are also written for Python 3, but have to be compatible with
Python 3.4 or newer. Since they are executed in various Python environments on
the monitored hosts, they should have as small dependencies as possible. Best is
to only rely on vanilla Python without 3rd party modules.

Use `#!/usr/bin/env python3` as shebang.

Besides the Python 3 variant, the agent plugins are also available for Python 2.
These Python 2 variants (`_2.py` ending in `agents/plugins`) are generated
automatically from the Python 3 scripts while packaging Checkmk. So no Python 2
script needs to be programmed. The Python 2 files are named `[plugin]_2.py`.
Have a look at `agents/plugins/Makefile` to see how we generate them.

The agent is automatically dealing with Python 2 and 3 plugins and environments
if possible.  If a `.py` file is found and a `python3` greater than or equal to
Python 3.4 is in the `PATH`, then this plugin is used.  If `_2.py` file is found
and there is a `python2` or `python` in the `PATH`, then this is used. It is
ensured that no plugin is executed in two versions.

Agent plugins are executed on monitored systems. Here we can not rely on the
presence of certain modules. The agent plugin + Check-Plugin must transport a
clean message to the user in the GUI, if a dependency is missing (see e.g.
Docker plugin).

For new plugins it is okay to use special dependencies, e.g. API bindings.  But
we have to take older Python versions and incompatibilities into account and
produce error agent sections + error messages that tell the user about this
issue.

---
**Known issues regarding 3to2 conversion**

- `f-strings`: Currently 3to2  cannot convert `f-strings` into `python2`
  compatible syntax. So use `format()` instead.
---

### Imports

Don't use star import like `from module import *`. They make it hard to
understand which names are really available and needed in the current namespace.

### Exception handling

* Easier to ask for forgiveness than permission

    ```python
    def get_status(file):
        if not os.path.exists(file):
            print("file not found")
            sys.exit(1)
        with open(file) as f:
            return f.readline()
    ```

    vs.

    ```python
    def get_status(file):
        try:
            with open(file) as f:
                return f.readline()
        except OSError as e:
            print("Unable to open file: %s" % e)
            sys.exit(1)
    ```

* Be as specific as possible when catching exceptions
* Keep try-blocks as small as possible
* Don't use `except:` (Slightly better for special cases: `except Exception`)

### Paths and files

* Use `pathlib`.
* Use context-managers (the `with` keyword) to open files.
* You are welcome to refactor old style file IO to pathlib (with tests :-))

### String formatting

* Use classic format strings (`%s`) for the time being. We'll move over to the
  new `format()` syntax in the future, but for the moment we'd like to stay
  consistent.

### Sub processes

* Use mechanisms that are natively available in Python instead of
  subprocess/command line tools. Example: Don't use `tar` command line tools.
  Use the `tarfile` module instead. There may be good reasons to go with the
  command line tools in special situations.

* Use secure methods for calling external programs to prevent shell injections
  * Use the `subprocess` module instead of `os.system()` or `os.popen()`
  * Use `shell=False` and `close_fds=True` with subprocess.
  * Use `pipes.quote()` in case you need to create a command line string

### Argument parsing

* Use `argparse`. In agent plugins, which have to support Python <2.5, use
  `optparse`.

### Logging

* Use logger or `cmk.log`, `cmk.gui.log` as base for logging
* Add a logger object to `self._logger` to all classes (Use either a
  class/object specific child logger, the module level `logger` or
  `cmk.log.logger`)
* Don't use format strings for log messages. Use: `logger.info('Hello, %s', world)`

### HTTP requests

* Use `requests`, it's great!
* Work with requests sessions in case you need to perform multiple requests

### Times and Dates

* Use top level functionality, e.g.: `datetime`, `dateutil`

### Comments

* Document the non-obvious. Don't document the how, do document the why.
* Use doc-strings for classes and methods.

### Code structuring

* Use the right data structure for combining data. For more complex code it
  is important to carefully think about this. This may help you find the right
  data structure for your data. In increasing order of preference:
    * Dictionaries: Worst possible representation. One has no clue whatsoever
      about the valid keys nor the valid values for a given key. In addition,
      they are mutable, which might not be what one wants. In effect, we are
      abusing a useful mapping type to simulate a struct.
    * Tuples of varying length: Basically the same as dictionaries with all the
      downsides.
    * Tuples of a fixed length: Slightly better, they have a fixed number of
      slots and are immutable. Still, one has no clue what a slot should mean.
    * `collections.namedtuple`: A bit better than tuples of a fixed length, at
      least the slots have names now. Still no clue about the valid values of a
      slot.
    * `typing.NamedTuple`: Kind of OK, slots have names and a type now. Still
      not really OO, because it is still a dumb data container, but at least we
      have reached a state where Pascal was in the 70s.
    * A `class`: This is almost what we want. Note: Classes with tons of
      static/class methods are actually //not// a class, they are a namespace
      in disguise, so we should not use them like that.
    * A `class` with mypy type annotations: This is the optimum.  Now we're
      talking OO and mypy can help us tremendously during e.g. refactorings.
* Don't use global variables unless you have to and can do so thread-safe.
* Don't assign attributes to function objects.
* Use `abc` for specifying abstract classes, methods and properties and add
  `raise NotImplementedError()` in abstract methods and properties)
* Make class attributes explicit in the constructor or helper functions (Don't
  add them dynamically e.g. via a dict argument and ''getattr()'')
* Extensive getter/setters: In Python it is acceptable to simply access class
  or object members directly. In case you want to protect things from external
  access make use of `@property`
* Use `@staticmethod` and `@classmethod` decorators for methods without
  references to `cls` or `self`
* Use early exits in your functions.

### Module: cmk

* The entire Python code of Checkmk should be under the main module `cmk` in
  the future
* Below `cmk.utils` there is a module that provides functionalities for all
  components. These can be imported from anywhere. e.g. below is
  `cmk.utils.log` for logging functionalities.
* At the first module level, the component modules are split up, e.g.:
  * `cmk.base`
  * `cmk.gui`
  * `cmk.ec`
* All names that a component declares on its main level may be loaded by other
  components.
  * Another approach may be to explicitly declare the exports in a dedicated
    sub module, e.g. `cmk.ec.export.`.
  * e.g. if the name `load_ec_rule_packs` is registered in `cmk/ec/__init__.py`,
    the GUI code may access `cmk.ec.load_ec_rule_packs`.
  * Names from submodules must not be imported from other components.
* For the CME/CEE there is a module hierarchy under `cmk/cee` or `cmk/cme`.
  The same rules apply as for `cmk` itself.

### Code formatting

* We supply an `.editorconfig` file, which is used to automatically configure
  your editor to adhere to the most basic formatting style, like indents or
  line-lengths. If your editor doesn't already come with Editorconfig support,
  install [one of the available plugins](https://editorconfig.org/#download).
* We use Black for automatic formatting of the Python code.
  Have a look [below](#automatic-formatting) for further information.
* We use isort for automatic sorting of imports in Python code.
* Multi line imports: Use braces instead of continuation character

    ```python
    from germany import bmw, \
        mercedes, \
        audi
    ```

    vs.

    ```python
    from germany import (
        bmw,
        mercedes,
        audi,
    )
    ```

### Automatic formatting with black and isort

The black configuration file, `pyproject.toml`, lives in the root directory of the
project repository, where Black picks it up automatically. Black itself lives in
a virtualenv managed by pipenv in `check_mk/.venv`, you can run it with
`make format-python-black` or `scripts/run-pipenv run black`.

The imports are also sorted with isort. Configuration is in `pyproject.toml`
file in the root directory of the project repository. If you have isort installed
in you virtualenv you can run it with `make format-python-isort`

#### Manual black invocation: Single file

```console
black [the_file.py]
```

#### Manual isort invocation: Single file

```console
$ isort [the_file.py]

# or with pre-commit installed
$ pre-commit run isort
```

#### Manual black invocation: Whole code base

If you want to black format all Python files in the repository, you can run:

```console
$ make format-python-black
```

#### Manual isort invocation: Whole code base

If you want to isort format all Python files in the repository, you can run:

```console
$ make format-python-isort
```

#### Integration with CI

Our CI executes black and isort formatting test on the whole code base:

```console
$ make -C tests test-format-python
```

Our review tests jobs prevent un-formatted code from being added to the
repository.

#### Editor integration with black:

[Black editor integration](https://black.readthedocs.io/en/stable/integrations/editors.html)

### Type checking: mypy

Code can be checked manually with `make -C tests test-mypy`.

The configuration file is `mypy.ini` and lives in the root directory of the
Checkmk repository. For info about how to type hint refer to
[mypy docs - Type hints cheat sheet (Python 2)](https://mypy.readthedocs.io/en/latest/cheat_sheet.html#type-hints-cheat-sheet-python-2).

#### vim

This is where [ALE](https://github.com/w0rp/ale) comes in again. To include mypy there adjust the following things in the `.vimrc`:

* Add mypy to the liners. With me it looks like this:

  ```vim
  let g:ale_linters = {
  \ 'python': ['pylint', 'mypy'],
  \ 'javascript': ['eslint'],
  \}
  ```

* Then tell the linter how to run pylint and mypy:

  ```vim
  let g:ale_python_mypy_executable = 'YOUR_REPO_PATH/check_mk/scripts/run-mypy'
  let g:ale_python_pylint_executable = 'YOUR_REPO_PATH/check_mk/scripts/run-pylint'
  let g:ale_python_pylint_options = '--rcfile YOUR_REPO_PATH/check_mk/.pylintrc'
  ```

---
**NOTE**

mypy may not support home expansion ("~"), so it is recommended to use an
absolute Path for 'YOUR_REPO_PATH'.

---

The mypy-Checker should run with this. With ":ALEInfo" you get information
about the error diagnosis below, if it doesn't work.

#### Editor integration: *macs

* The mypy.ini should be found by Flycheck without further configuration.
* To use the correct mypy executable a `.dir-locals.el` in the root directory
  of the Checkmk repository is used.
* Flycheck by default does not execute multiple checkers. To enable the mypy
  checker after the pylint checker the following snippet can be used e.g. in
  the `dotspacemacs/user-config`:

  ```lisp
    (with-eval-after-load 'flycheck
      (flycheck-add-next-checker 'python-pylint 'python-mypy))
  ```

* To disable the risky variable warning that is triggered by setting the mypy
  executable the `safe-local-variables` variable has to be extended by:

  ```lisp
  (eval setq flycheck-python-mypy-executable
             (concat
              (projectile-locate-dominating-file default-directory dir-locals-file)
              "scripts/run-mypy"))
  ```

* An example value of the `safe-local-variables` variable is e.g.:

  ```lisp
  ((eval setq flycheck-python-mypy-executable
         (concat
          (projectile-locate-dominating-file default-directory dir-locals-file)
          "scripts/run-mypy"))
   (py-indent-offset . 4)
   (encoding . utf-8))
  ```

## Shell scripts

The Linux / Unix agents and several plugins are written in shell code for best
portability and transparency. If you would like to change or contribute
something, please respect the following things:

### Is it appropriate

#### Contributed Plugins and Local Checks

If you think you need to use more advanced (read: less portable) shell
capability for your plugin or local check, such as associative arrays found in
e.g. `bash`, `zsh`, then you should probably consider using another language
like `python`.

If you're only familiar with shell, or it's all that's available to your
particular situation, that's fine, but you should:

* Put a comment in your code stating that you're open to having your check or
  plugin rewritten, or why you don't want it rewritten
* Fail-fast, fail-early e.g

```bash
# Restrict this plugin script to bash 4 and newer
if [[ -z "${BASH_VERSION}" ]] || (( "${BASH_VERSINFO[0]}" < 4 )); then
  printf -- '%s\n' "This check requires bash 4 or newer" >&2
  exit 1
fi
```

#### Contributions to the agent scripts

If you think you need to use more advanced shell capability for the agent code,
then you will need to find another way to achieve what you want to do.

### Code style

Format your code according to the following guidelines:

* [ChromiumOS's Shell Style Guidelines](https://chromium.googlesource.com/chromiumos/docs/+/master/styleguide/shell.md)
* [Google's Shell Style Guidelines](https://google.github.io/styleguide/shell.xml)

checkmk specific guidance below supersedes what's offered in those guidelines:

### Indentation and column width

* Line length up to 100 characters is allowed
* Use 4 spaces for indentation

### Function Names

Names are in lowercase, underscored i.e. `snake_case()`.  Names should be
meaningful, so the `verb_noun` style may be worth considering.  Microsoft has
documentation for [approved
verbs](https://docs.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands?view=powershell-7)
that may provide some useful guidance.

The Google/ChromiumOS style guides allow for `class::function()` style names,
but do note that this does not appear to be portable.  No workaround is
suggested at this time, but we expect something like `__class_function()` may
be suitable.

Do not use the `function` keyword.  It is non-portable and considered obsolete.

Bad:

```bash
# Haha I gave this function a funny name!
function blurgh() {
    ...
}
```

Better:

```bash
get_checkmk_api() {
    ...
}
```

### Variables and Constants

#### Typing

Variables in Linux/UNIX shells are untyped.  Attempts have been made to bring in
some degree of typing via `typeset` and `declare`, but these are not portable
solutions, so should be avoided.

If you need a variable to be of a specific type, the best advice right now
(that we're aware of) is to validate it before you use it.

#### Pseudoscoping

We practice psuedoscoping to minimise the chances of variables within scripts or
functions from clobbering variables within the environment and vice versa.

Variables must be in the appropriate format for its "scope" as defined below:

##### Environment

We know from long-established convention that *environment* variables are
almost always in UPPERCASE.  You can see this in e.g. `bash` by running `set`
and/or `printenv`.

We generally shouldn't need to put any variables into the environment, so you
should avoid UPPERCASE as much as possible.  If you *do* need a variable
in the environment "scope" for whatever reason, use the form `MK_VARNAME`
e.g. `MK_VERSION`

You might often see this "scope" referred to as the *global* scope, or *shell*
scope.  This scope also contains shell builtin variables.

##### Script

Variables in the *script* "scope" tend often to be mistakenly written in
UPPERCASE, which gives rise to the possibility of clobbering a legitimate
variable in the *environment* "scope".  This can have results that are
[potentially hilarious, or potentially bad](https://stackoverflow.com/q/28310594)
depending on your point of view.

For that reason, UPPERCASE variable names are strongly discouraged outside of
the *environment* scope.

Instead, use lowercase, with underscores to separate words i.e. `snake_case`.

GNU Autoconf's documentation also states:

>As a general rule, shell variable names containing a lower-case letter are safe;
>you can define and use these variables without worrying about their effect on
>the underlying system, and without worrying about whether the shell changes
>them unexpectedly.

Try, also, to use meaningful names.  This is meaningless:

```bash
for f in $(lsblk -ln -o NAME); do
    ...
```

Whereas this is better:

```bash
for block_device in $(lsblk -ln -o NAME); do
    ...
```

This also reduces/eliminates unexpected in-scope collisions.

*Exception:*
*C-Style `for (( i=0; i<max_count; i++ )); do` style loops,*
*as the var `i` is usually self-contained and is short-hand for 'integer'*

You should consider `unset`ting your variables once you're done with them,
though this isn't strictly necessary.

##### Function / Local

`bash` and others allow you to define variables as local within a function e.g.

```bash
get_api_user() {
    local username
    username=Shelly
    ...
}
```

Unfortunately this is not portable and attempts at workarounds are...
[somewhat hackish](https://stackoverflow.com/q/18597697).  So our approach to
solve this is to simply prepend any variables within a function with an
underscore. We also `unset` the variable immediately prior to the function
closure.  For example:

```bash
get_api_user() {
    _username=Shelly
    ...
    unset -v _username
}
```

##### Curly braces

Curly braces are used on `${arrays[@]}` and `${variable/modif/ications}`.
To maintain consistency, you should use curly braces on normal variables too.

Curly braces around variables improves readability when syntax colouring is not
available.  ${this_variable} stands out within this block of text.

They also allow us to more robustly format outputs e.g.

```console
$ time_metric=5
$ echo "$time_metricmins"

$ echo "${time_metric}mins"
5mins
```

In the first example, there is no such variable as `$timemetricmins`.

In the second example, the curly braces explicitly tell the shell interpreter
where the variable name boundaries are.  Instead of applying this via trial and
error, the simplest approach is to just use curly braces by default.

*Exception: When you're in an arithmetic context e.g. `$(( time_metric + 10 ))`*

*Exceptions to the exception: If your var is an array element or requires*
*transformation e.g.*

* *`$(( "${time_metrics[2]}" + 20 ))`*
* *`$(( "${10#time_metric}" + 10 ))`*

##### Constants

To make a variable constant (a.k.a. an "immutable variable"), use `readonly`,
defined and set separately e.g.

```bash
MK_CONSTANT="Polaris"
readonly MK_CONSTANT
```

#### Variable pseudoscopes re-cap

* **Environment**:       `${MK_UPPERCASE}`
* **Script**:            `${meaningful_snake_case}`
* **Function / Local**:  `${_underscore_prepended_snake_case}` with `unset -v`
* **Constants**:         The appropriate above form set to `readonly`

### Linting

Use [shellcheck](https://www.shellcheck.net/) for your changes before
submitting patches.

The best results are achieved with
[a direct integration](https://github.com/koalaman/shellcheck#user-content-in-your-editor)
into your preferred editor, so that you are immediately informed about
possible problems during programming.

The various agent scripts are not clean at the moment, but we aim to clean
this up in the near future.

Do note that while Shellcheck is an excellent tool, it's not perfect.
Sometimes it alerts on code that may actually be desired.  In this scenario,
you must use a `disable` directive with a comment that justifies your reason
for this.  It may also be useful to reference a git commit hash or werk number.

```bash
# This function is sourced outside of this library, where it does parse args
# See commit abcd3456 and/or werk 1234
# shellcheck disable=SC2120
foo() {
```

### Formatting

You may use [shfmt](https://github.com/mvdan/sh) to help with formatting.

If you don't have a Go environment ready, the easiest way is to use it is using
a prepared docker image (See bottom of project README). We have a shortcut to
this, which is also used by our CI system.

Execute this in checkmk git directory:

```console
$ sudo docker run --rm -v "$(pwd):/sh" -w /sh peterdavehello/shfmt shfmt -i 4 -ci -w agents/check_mk_agent.linux
```

### Portability

* We are loosely aiming for "POSIX plus simple named arrays"

* `echo` is a portability nightmare.  Prefer `printf` instead.

* Existing scripts have been written using a variety of shells.  Scripts that
  use `bash` have tended to be written for `bash` 3.x.

* In the future, we will attempt to make our shell code more portable, which
  means reducing `bash`isms.  If you're making shell code now, try to approach
  it with portability in mind. Your code may be used on older systems and/or
  commercial unices (e.g. AIX, Solaris etc).

* `ksh` is in some ways a reasonable lowest common denominator to target as it's
  [virtually everywhere](https://www.in-ulm.de/~mascheck/various/shells/), and
  its syntax is almost directly runnable in `bash`, `zsh` and others.  Be aware,
  however, that there are many variants of `ksh`.  [`oksh`](https://github.com/ibara/oksh)
  is a decent variant.

* Ubuntu's [DashAsBinSh](https://wiki.ubuntu.com/DashAsBinSh) wiki page can give
  you some ideas on more portable scripting, and `dash` is a readily available
  shell that you can test your code within.  Do be aware that `dash` is stricter
  than our goals.

* The needs of `busybox ash` (i.e. for `openwrt`) may also be something to consider

* A tool like [shall](https://github.com/mklement0/shall) might be useful

### The Unofficial Strict Mode

There is a lot of advice on the internet to "always use The Unofficial Strict Mode."

It is usually presented as a brilliant catch-all that will magically fix every
shell scripting issue.  It is usually in a form similar to:

```bash
set -euo pipefail
```

This is well meaning, but flawed advice.  Firstly, it's not portable, so it's
disqualified by default for our purposes.  Secondly, it comes with its own flaws.
Some of these options have reasonable uses, but it's dangerous to think that
this one-line incantation is somehow perfect.  You can read more about it, and
specifically `set -e` at one of the following links (read *at least* the first):

* <https://www.reddit.com/r/commandline/comments/g1vsxk/the_first_two_statements_of_your_bash_script/fniifmk/>
* <http://wiki.bash-hackers.org/scripting/obsolete>
* <http://mywiki.wooledge.org/BashFAQ/105>
* <http://mywiki.wooledge.org/BashFAQ/112>
* <https://www.reddit.com/r/bash/comments/8asn1e/trying_to_understand_a_script_to_delete_all_but/dx1y785/>

### Performance

Let's be honest: Compared to almost anything else, shell performance is
suboptimal.  Especially in `bash`.  We use shell for Linux/UNIX hosts because,
for better or worse, it is the most portable option.  Nonetheless, we can at
least try to be mindful about how we construct our code, in order to squeeze out
as much performance as we can.

It may help to think of this competitively, or as a challenge.  Constantly ask
yourself "can I optimize this code any further?"

For a simple and classic example, we have the good old
["Useless Use of Cat"](http://porkmail.org/era/unix/award.html):

```bash
cat haystack.txt | grep needle
```

This causes a pointless fork and process, as well as a waste of a pipe with
associated buffering and broken pipe risks, as `grep` can address files directly
i.e.

```bash
grep needle haystack.txt
```

We also often find "Useless Use of Cat" paired with "Useless Use of Grep | Awk"
e.g.

```bash
cat haystack.txt | grep needle | awk '{print $2}'
```

`awk`, like `grep`, can address files directly, and given that it has searching
built in, it can actually do all of this in one shot:

```bash
awk '/needle/{print $2}' haystack.txt
```

Or to do so case insensitively:

```bash
awk 'tolower($0) ~ /needle/{print $2}' haystack.txt
```

Often we see blocks of `if...elif...elif...elif`'s that can and should be
replaced with a cleaner and meaner `case...esac` statement.

The style guides linked to earlier both state:

>Given the choice between invoking a shell builtin and invoking a separate
>process, choose the builtin.
>
>We prefer the use of builtins such as the Parameter Expansion functions in
>bash(1) as it’s more robust and portable (especially when compared to things
>like sed).

Often (but not always) there are massive performance gains to be had through
the use of builtins, usually at the expense of some readability.  This can be
counter-balanced via explanatory comments.

## Localization

The user interface of Checkmk can be localized using [Weblate](https://translate.checkmk.com/).
We are very happy about any contributions to the localization of Checkmk. To
contribute, please first register an account at our Weblate server. Afterwards,
you can iterate through untranslated source strings and localize them. See this
[forum post](https://forum.checkmk.com/t/about-the-localization-category/21578)
for further information.

Please note that any PRs which directly edit the PO-files will be disregarded,
since the localization should be done exclusively via Weblate to avoid merge
conflicts.

### Translation of technical terms

Technical terms outside of Checkmk like "container" may be translated according
to the common usage for that technology.

There are several terms in Checkmk that may be kept for a better understanding.
Some of them are:

* Host
* Service
* Check
* Item
* DOWN, UP, PENDING

### Consistency

Be consistent in the terms you use for a thing. E.g. in case for a server one
could say something like "host", "system", "server" or "device". Decide to use
one name for one thing and use it consistently in all translations.

## Copyright and Licensing

The open source part of Checkmk is licensed under the terms of the [GNU GPLv2
License](COPYING). Any new code must be compatible with those terms.

To ensure that, please always add our current licensing information to any new
files you want to contribute. The licensing information can be found at the beginning
of already existing files and looks something like

```python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
```
