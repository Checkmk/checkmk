# Contributing to Checkmk

We welcome contributions to [Checkmk on Github](https://github.com/tribe29/checkmk).

Most contributions to Checkmk are small bug-fixes, enhancements of existing
features, or completely new plugins. The guidelines below address these types
of contributions.

If you would like to make a major change to Checkmk, please contact us first.
Let's talk about what you want to do. Somebody else may already be working on
it, or there are certain topics you should know before implementing the change.

We love to work with community contributors and want to make sure contributions
and time investments are as effective as possible. That's why it is important
to us to discuss major changes you might be planning in order to jointly agree
on the best solution approach to the problem at hand. This preempts potential
issues during the code reviews of pull requests.

## Contributing code

In general, we follow the standard GitHub workflow which roughly works like
this:

 1. **Fork** the repository on GitHub
 2. **Clone** the forked repository to your own machine
 3. **Commit** changes to your own feature branch
 4. **Push** your work back up to your forked repository
 5. Submit a **Pull request** (PR) so that we can review your changes

Have a careful look at the following chapters if your are working like this for
the first time. The following document also includes a lot of details about our
coding standards, needed tools and so on.

## How to prepare for contributing?

We are developing Checkmk on **Ubuntu Linux** systems. It's not a hard requirement, but
most helper scripts are optimized for this, so we highly recommend it for best
experience.

To set up the development environment do the following:

- Setup a Checkmk source code working copy on your computer

  First you need a local fork of the Checkmk git. To create it, press the
  *fork* button on the Checkmk GitHub page. This will create a copy of the
  repository in your own GitHub account and you'll see a note that it’s been
  forked as: *YourName/checkmk*.

  You now need to clone your own copy to your computer.  This can be done using
  the command line on your computer:

  We do this from `~/git` directory. This will result in a `~/git/checkmk`
  directory.

  ```
  $ mkdir ~/git
  $ cd ~/git
  $ git clone git@github.com:YourName/checkmk.git
  ```

- Then change to the just created project directory.

  ```
  $ cd checkmk
  ```

- Install development dependencies

  Before you can start working on Checkmk, you will have to install some
  additional software, like tools for development and testing. Execute this in
  the project directory:

  ```
  $ make setup
  ```

  > This is optimized for Ubuntu, but you may also get all the required programs
  > on other platforms.

  After the dependencies have been installed, you could execute the shipped
  tests to ensure everything is working fine before start making changes to
  Checkmk.
  If you like to do this, please have a look at the [How to execute tests?](#how-to-execute-tests)
  chapter.

- Install pre-commit checks

  In order to keep your commits to our standard we provide a [pre-commit](https://pre-commit.com/)
  configuration and some custom made checking scripts. You can install it like this:

  > Warning: Python3 is required for pre-commit! Installing it with Python 2 will break
  > your environment and leave you unable to use pip due to a backports module clash!

  ```
  pip3 install pre-commit
  ```

  After successful installation, hook it up to your git-repository by issuing the following command inside your git repository:

  ```
  pre-commit install --allow-missing-config
  ```
  The `--allow-missing-config` parameter is needed so that branches of older versions of Checkmk which don't
  support this feature and are missing the configuration file won't throw errors.

  Afterwards your commits will automatically be checked for conformity by `pre-commit`. If you know a
  check (like mypy for example) got something wrong and you don't want to fix it right away you can skip
  execution of the checkers with `git commit -n`. Please don't push unchecked changes as this will
  introduce delays and additional work.

  Additional helpers can be found in `scripts/`. One noteable one is `scripts/check-current-commit`
  which checks your commit *after* it has been made. You can then fix errors and amend or squash
  your commit. You can also use this script in a rebase like such:

  ```
  git rebase --exec scripts/check-current-commit
  ```

  This will rebase your current changes and check each commit for errors. After fixing them you can
  then continue rebasing.


Once done, you are ready for the next chapter.

## How to change Checkmk?

The number one rule is to *put each piece of work on its own branch*. In most of
the cases your development will be based on the *master* branch. So lets start
like this:

```
$ git checkout master
$ git checkout -b my-feature-branch
```

The first command ensures you start with the master branch. The second command
created the branch `my-feature-branch`. Pick some descriptive name you can remember
later.

Let's check if everything worked fine:

```
$ git status
On branch my-feature-branch
(...)
```

Now start developing and create one or multiple commits.

**Important**: Do one thing in one commit, e.g. don't mix code reorganization and
changes of the moved lines. Separate this in two commits.

Make sure that you commit in logical blocks and write [good commit messages](#style-guide-commit-messages).

If you have finished your work, it's a good time to [execute the tests locally](#how-to-execute-tests)
to ensure you did not break anything.

Once you are done with the commits and tests in your feature branch you could
push them to your own GitHub fork like this.

```
$ git push -u origin my-feature-branch
```

In the output of this command you will see a URL which you can open to create
a pull request from your feature branch.

On GitHub in your browser, submit a pull request from your `my-feature-branch`
to the official Checkmk branch you forked from.

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

```
git remote add upstream https://github.com/tribe29/checkmk.git
```

From now, you can always update your feature branches with this command:

```
git pull --rebase upstream master
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

## How to execute tests?

The public repository of [Checkmk](https://github.com/tribe29/checkmk) is
integrated with Travis CI. Each time a Pull request is submitted, Travis will
have a look at the changes.

**Important:** We only review PRs that are confirmed to be OK by Travis.

It is recommended to run all tests locally before submitting a PR. If you want
to execute the full test suite, you can do this by executing these commands in
the project base directory:

```
$ make -C tests test-pylint
$ make -C tests test-bandit
$ make -C tests test-unit
$ make -C tests test-python-futurize
$ make -C tests test-format-python

$ make -C tests-py3 test-pylint
$ make -C tests-py3 test-unit
$ make -C tests-py3 test-mypy-raw
```

Some of these commands take several minutes, for example the command
`test-format-python` because it tests the formatting of the whole code base.
Normally you only change a small set of files in your commits. If you execute
`yapf -i [filename]` to format the changed code, this should be enough and you
don't need to execute the formatting test at all.

> We highly recommend to integrate yapf, pylint and mypy into the editor you
> work with. Most editors will notify you about issues in the moment you edit
> the code.

You could also push your changed to your forked repository and wait for Travis
to execute the tests for you, but that takes several minutes for each try.

## Style guide: Guidelines for coding check plug-ins

Respect the [Guidelines for coding check plug-ins](https://checkmk.com/cms_dev_guidelines.html).

## Style guide: Commit messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- The first line is a short title (limit to 72 characters or less)
- Reference issues and pull requests liberally after the first line
- Write [good commit messages](https://chris.beams.io/posts/git-commit/)

## Style guide: Python

The guidelines listed here are binding for the development at Checkmk in
Python.

This list is intended to grow in practice and does not claim to be exhaustive.

First orientate yourself on the existing code. If it doesn't fit these
guidelines at all, it might be better to first orientate yourself on the
existing code and adapt the code to these guidelines separately from any
content changes.

[Zen of Python](https://www.python.org/dev/peps/pep-0020/).

Checkmk is mostly written in Python. At the moment the most of the code base is
using Python 2.7. We are already preparing to change to Python 3, but this will
take some time. We plan to finish this until 2020. For the moment Python 2.7 is
the language to use.

Only rely on non-standard modules that are mentioned in the `Pipfile`.
<!--- TODO: How to add new modules? -->

### Agent plugins: Supported Python versions

The agent plugins need to be executed on older Linux systems which may
have very old Python versions available. For this reason we need to use
the old Python 2.5 compatible syntax here.

On the monitored host we use Python for some popular agent plugins (like
`mk_logwatch`).  These are currently built to support Python 2.5 to Python 2.7.

Python plugins that are incompatible to 2.5, for example because some 3rd party
library is not available with 2.5, need to be syntax compatible with 2.5 for
the moment, but are allowed to terminate with a helpful error message about
this incompatibility.

Use `#!/usr/bin/env python` as shebang.

Completely new plugins should be written to be compatible with Python 2.7 and
Python 3.

In case you want to explicitly create a Python 3 agent plugin, use
`#!/usr/bin/env python3` as shebang.

### Imports

Don't use star import like `from module import *`. They make it hard to understand which
names are really available and needed in the current namespace.

### Exception handling

- Easier to ask for forgiveness than permission

    ```
    def get_status(file):
        if not os.path.exists(file):
            print "file not found"
            sys.exit(1)
        return open(file).readline()
    ```

    vs.

    ```
    def get_status(file):
        try:
            return open(file).readline()
        except EnvironmentError as e:
            print "Unable to open file: %s" % e
            sys.exit(1)
    ```

- Be as specific as possible when catching exceptions
- Keep try-blocks as small as possible
- Don't use `except:` (Slightly better for special cases: `except Exception`)

### Paths and files

- Use `pathlib2` / `pathlib` (in Python 3). To be more future-proof, import like this:

  ```
  from pathlib2 import Path
  ```

- Use context-managers (the `with` keyword) to open files.
- You are welcome to refactor old style file IO to pathlib (with tests :-))

### String formatting

- Use classic format strings (`%s`) for the time being. We'll move over to the
  new `format()` syntax in the future, but for the moment we'd like to stay
  consistent.

### Sub processes

- Use mechanisms that are natively available in Python instead of
  subprocess/command line tools. Example: Don't use `tar` command line tools.
  Use the `tarfile` module instead. There may be good reasons to go with the
  command line tools in special situations.

- Use secure methods for calling external programs to prevent shell injections
  - Use the `subprocess` module instead of `os.system()` or `os.popen()`
  - Use `shell=False` and `close_fds=True` with subprocess.
  - Use `pipes.quote()` in case you need to create a command line string

### Argument parsing

- Use `argparse`. In Checkmk where we have Python 2.7. In agent plugins, which
  have to support Python <2.5, use `optparse`.


### Logging

- Use logger or `cmk.log`, `cmk.gui.log` as base for logging
- Add a logger object to `self._logger` to all classes (Use either a
  class/object specific child logger, the module level `logger` or
  `cmk.log.logger`)
- Don't use format strings for log messages. Use: `logger.info('Hello, %s', world)`

### HTTP requests

- Use `requests`, it's great!
- Work with requests sessions in case you need to perform multiple requests

### Times and Dates

- Use top level functionality, e.g.: `datetime`, `dateutil`

### Comments

- Document the non-obvious. Don't document the how, do document the why.
- Use doc-strings for classes and methods.

### Code structuring

- Use the right data structure for combining data. For more complex code it
  is important to carefully think about this. This may help you find the right
  data structure for your data. In increasing order of preference:
    - Dictionaries: Worst possible representation. One has no clue whatsoever
      about the valid keys nor the valid values for a given key. In addition,
      they are mutable, which might not be what one wants. In effect, we are
      abusing a useful mapping type to simulate a struct.
    - Tuples of varying length: Basically the same as dictionaries with all the
      downsides.
    - Tuples of a fixed length: Slightly better, they have a fixed number of
      slots and are immutable. Still, one has no clue what a slot should mean.
    - `collectons.namedtuple`: A bit better than tuples of a fixed length, at
      least the slots have names now. Still no clue about the valid values of a
      slot.
    - `typing.NamedTuple`: Kind of OK, slots have names and a type now. Still
      not really OO, because it is still a dumb data container, but at least we
      have reached a state where Pascal was in the 70s.
    - A `class`: This is almost what we want. Note: Classes with tons of
      static/class methods are actually //not// a class, they are a namespace
      in disguise, so we should not use them like that.
    - A `class` with mypy type annotations: This is the optimum.  Now we're
      talking OO and mypy can help us tremendously during e.g. refactorings.
- Don't use global variables unless you have to and can do so thread-safe.
- Don't assign attributes to function objects.
- Use `abc` for specifying abstract classes, methods and properties and add
  `raise NotImplementedError()` in abstract methods and properties)
- Make class attributes explicit in the constructor or helper functions (Don't
  add them dynamically e.g. via a dict argument and ''getattr()'')
- Extensive getter/setters: In Python it is acceptable to simply access class
  or object members directly. In case you want to protect things from external
  access make use of `@property`
- Use `@staticmethod` and `@classmethod` decorators for methods without
  references to `cls` or `self`
- Use early exits in your functions.

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

- We supply an `.editorconfig` file, which is used to automatically configure
  your editor to adhere to the most basic formatting style, like indents or
  line-lengths. If your editor doesn't already come with Editorconfig support,
  install [one of the available plugins](https://editorconfig.org/#download).
- We use YAPF for automatic formatting of the Python code.
  Have a look [below](#automatic-formatting) for further information.
- Multi line imports: Use braces instead of continuation character

    ```
    from germany import bmw, \
        mercedes, \
        audi
    ```

    vs.

    ```
    from germany import (
        bmw,
        mercedes,
        audi,
    )
    ```

### Automatic formatting

The style definition file, `.style.yapf`, lives in the root directory of the
project repository, where YAPF picks it up automatically. YAPF itself lives in
a virtualenv managed by pipenv in `check_mk/virtual-envs/2.7/.venv`, you can run it with
`make format-python` or `scripts/run-pipenv run yapf`.

#### Manual invocation: Single file

```
yapf -i [the_file.py]
```

#### Manual invocation: Whole code base

If you want to format all Python files in the repository, you can run:

```
make format-python
```

#### Integration with CI

Our CI executes the following formatting test on the whole code base:

```
make -C tests test-format-python
```

Our review tests jobs prevent un-formatted code from being added to the
repository.

#### Editor integration: *macs

- plugins for vim and emacs with installation instructions can be found here:
  https://github.com/google/yapf/tree/master/plugins
- in Spacemacs yapfify-buffer is available in the Python layer; formatting on
  save can be enabled by setting ''python-enable-yapf-format-on-save'' to
  ''t''
- In Emacs with elpy call the function 'elpy-yapf-fix-code'. Because there
  are many large files you may want to increase the timeout for rpc calls by
  setting ''elpy-rpc-timeout'' to ''20''

#### Editor integration: vim

- It is recommended to use yapf as fixer for [ALE](https://github.com/dense-analysis/ale)

Configure YAPF as fixer in your `~/vimrc`. This way the file gets fixed on every save:

```
let g:ale_fixers = {'python': ['isort']}
let g:ale_fix_on_save = 1
```

- for vim formatting on save should work with [autocmds](http://learnvimscriptthehardway.stevelosh.com/chapters/12.html)

### Type checking: mypy

Code can be checked manually with `make -C tests-py3 test-mypy`.

The configuration file is `mypy.ini` and lives in the root directory of the
Checkmk repository. For info about how to type hint refer to
[mypy docs - Type hints cheat sheet (Python 2)](https://mypy.readthedocs.io/en/latest/cheat_sheet.html#type-hints-cheat-sheet-python-2).

#### vim

This is where [ALE](https://github.com/w0rp/ale) comes in again. To include mypy there adjust the following things in the `.vimrc`:

- Add mypy to the liners. With me it looks like this:

  ```
  let g:ale_linters = {
  \ 'python': ['pylint', 'mypy'],
  \ 'javascript': ['eslint'],
  \}
  ```

- Then tell the linter how to run mypy:

  ```
  let g:ale_python_mypy_executable = 'scripts/run-mypy'
  let g:ale_python_mypy_options = '--config-file=../mypy.ini'
  ```

The mypy-Checker should run with this. With ":ALEInfo" you get information
about the error diagnosis below, if it doesn't work.

#### Editor integration: *macs

- The mypy.ini should be found by Flycheck without further configuration.
- To use the correct mypy executable a `.dir-locals.el` in the root directory
  of the Checkmk repository is used.
- Flycheck by default does not execute multiple checkers. To enable the mypy
  checker after the pylint checker the following snippet can be used e.g. in
  the `dotspacemacs/user-config`:

  ```
    (with-eval-after-load 'flycheck
      (flycheck-add-next-checker 'python-pylint 'python-mypy))
  ```

- To disable the risky variable warning that is triggered by setting the mypy
  executable the `safe-local-variables` variable has to be extended by:

  ```
  (eval setq flycheck-python-mypy-executable
             (concat
              (projectile-locate-dominating-file default-directory dir-locals-file)
              "scripts/run-mypy"))
  ```

- An example value of the `safe-local-variables` variable is e.g.:

  ```
  ((eval setq flycheck-python-mypy-executable
         (concat
          (projectile-locate-dominating-file default-directory dir-locals-file)
          "scripts/run-mypy"))
   (py-indent-offset . 4)
   (encoding . utf-8))
  ```


## Style guide: Shell scripts

The Linux / Unix agents and several plugins are written in shell code for best
portability and transparency. In case you want to change something respect the
following things:

- Bash scripts are written for Bash version 3.1 or newer
- Set `set -e -o pipefail` at the top of your script
- Use [shellcheck](https://www.shellcheck.net/) for your changes before
  submitting patches.

  The best results are achieved with a direct integration into the editor, so
  that you are immediately informed about possible problems during programming.
  The agent itself is not clean at the moment, but we aim to clean this up in
  the near future.

- Format the code according to the [Google's Shell Style Guidelines](https://google.github.io/styleguide/shell.xml) with these exceptions:
  - Line length up to 100 characters is allowed
  - Use 4 spaces for indentation

- You may use [shfmt](https://github.com/mvdan/sh) to help with formatting.

  If you don't have a Go environment ready, the easiest way is to use it is using
  a prepared docker image (See bottom of project README). We have a shortcut to
  this, which is also used by our CI system.

  Execute this in Checkmk git directory:

```
  sudo docker run --rm -v "$(pwd):/sh" -w /sh peterdavehello/shfmt shfmt -i 4 -ci -w agents/check_mk_agent.linux
```

## Localization

The User interface of Checkmk can be localized. Currently we maintain a German
localization of Checkmk for all users. We are open to support other languages
when the localization is in a good state and nearly complete.

If you are interested: We can use [POEditor.com](https://poeditor.com) for
upstream localizations. Please contact us if you are interested.

### Translation of technical terms

Technical terms outside of Checkmk like "container" may be translated according
to the common usage for that technology.

There are several terms in Checkmk that may be kept for a better understanding.
Some of them are:

- Host
- Service
- Check
- Item
- DOWN, UP, PENDING

### Consistency

Be consistent in the terms you use for a thing. E.g. in case for a server one
could say something like "host", "system", "server" or "device". Decide to use
one name for one thing and use it consistently in all translations.


## Copyright and Licensing

The open source part of Checkmk is licensed under the terms of the [GNU GPLv2
License](COPYING). Any code brought in must be compatible with those terms.

You need to make sure that the code you send us in your pull request is GPLv2
compatible.
