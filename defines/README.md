# Checkmk Definition of Truth
--------------------------------------------------------------------------------

This file is meant as the 'one spot' to put information about requirements,
agreements and ideas about branch specific information used in development, CI
and DevOps contexts like

* versions of packages/components and tools
* supported editions and Linux distributions
* Meta-Information about Checkmk (like version)


## Requirements
--------------------------------------------------------------------------------

.. to keep in mind when changing values/formats of files or making agreements

* All agreements, requirements and upcoming changes in this context should be
  documented in here
* Changes to this file should pass the usual review process with members of
  affected teams added as reviewers (in order to avoid WIP on related topics
  without coordination)
* Clear responsibility among teams / certain individuals should be made sure
  for all items listed in this document.
* This file should list all scenarios to keep in mind and consider when changing
  values/formats (see next subsection)
* All definitions in this context should (as far as possible) be maintained in
  files located in this folder and be kept as non-redundant as possible
* File formats easy to access/use even in bash, Groovy, Python, Bazel, etc.
* As many information needed to build/develop should be available in current
  checkout


### Scenarios
--------------------------------------------------------------------------------

#### "Checkmk developer" usual workflow

A typical Checkmk developer works on a `checkmk` clone and needs all information
and credentials needed to build/debug/test all components they work on.

* Speed/efficiency is important, i.E.
    - most 'typical' modifications to the code base must be able to evaluate /
      apply in only a couple of seconds
    - also a 'CI roundtrip' should only be a couple of minutes

* TBD: What are the different "types" of Checkmk developers with different
    needs, i.e. some workflows might priorize aspects like quick roundtrips,
    while others struggle with reliabliliy/reproducability.. e.g.
    - "Check-developer" might want to quickly apply changes to Python files by
      just copying them
    - "Core developer" needs toolchain to run natively and quickly
    - "UI developer"..
    - What else? (TBD)


#### CI Tests / Gerrit

stub


#### CI Package build process

* Safety regarding deliverables (e.g. versions of components contained in
  customer facing artifacts)


#### Release process

stub


#### Tool context

* Docker-contexts
* Bazel (WORKSPACE)


#### External developer

stub


#### "Public developer" clones the `checkmk`-repository on GitHub and works with it

stub


#### "Some other internal workflow"

e.g. documentation / website related needs to access information like BOM, werks, etc

stub


## Content / specific information / location
--------------------------------------------------------------------------------

This is a TBD-list of current sources of truth which might/should be
consolidated, unified and brought together (or reasons for why not):

* [ ] Stuff from `defines.make`
* [ ] Credentials (pypi-mirror, Jenkins, Bazel, ..) (or recipies for how to get them)
* [ ] Checkmk version (and artifact version strings)
* [ ] Component versions
    * Python version (together with other possible versions of tools)
    * Perl
* [ ] `stages.yml` (information about test steps)
* [ ] Docker Image Aliases (Pinned Docker images)
* [ ] `Pipfile` (as far as possible)
* [ ] package dependency-paths (i.e. the paths formerly specified in Jenkins-jobs
      triggered only on changes in those directories, (e.g. for agents))
      (currently stored in JJB/Jenkins-Jobs/Groovy files)
* [ ] OMD-package sources (i.e. urls/sha used by Bazel but in different contexts and
      also at different places, like Python version)
* [ ] Stuff from `editions.yaml` / supported / used distros per edition / context
* [ ] Tooling (e.g. `run-ci`, `checkmk-dev-tools`)
* [ ] Werks


After the above items have been handled, this chapter might be removed.


## Files
--------------------------------------------------------------------------------

The following sections list stuff already implemented and should be seen as
examples for newly added elements. In general

### `test-steps.yaml`

* Path: `defines/test-steps.yaml`
* Format: YAML
* Description:
    Lists single tests-steps executed by the generic change-validation job
    triggered by Gerrit, e.g. `checkmk/master/change_validation/test-gerrit/`
* Interfaces:
    Proprietary - list of named test steps being executed together with
    environment variables being evaluated
* Consumers:
    - CI / Gerrit triggered Change Validation Pipeline
    - Local execution of same steps by invoking the `make-what-gerrit-makes`
      make target or by running
        ```sh
        scripts/run-uvenv buildscripts/scripts/validate_changes.py \
            -e BASE_COMMIT_ID=origin/master \
            -e WORKSPACE="$(pwd)" \
            -e RESULTS="$(pwd)/results"
        ```
      manually

* Future plans
    - File should also contain all other (non `test-gerrit`) tests and used in
      all other test pipelines
    - Test-Steps should be "container-agnostic" i.e. run all test steps natively
      enabling the CI using it's own way to run container


### `editions.yaml`

Contains edition-specific information like supported distros per edition,
targeted distros for specific tests, etc.

Read by: TBD


## Example
--------------------------------------------------------------------------------

To be vanished

This is not a proposal, but tries to make things clear

```
/defines/
 ├── Readme.md                  # This file
 ├── pyproject.toml             # Python Package dependencies - might have to be top-level
 ├── testing.yaml               # stages.yml but better
 ├── editions.yaml              # Information about edition specific stuff like distros, etc
 ├── external-packages.json     # contains urls/shas
 .
 .
 └── docker-image-aliases       # contains image pins
   ├── IMAGE_UBUNTU_22_04
   ├── IMAGE_DEBIAN_9
   └── IMAGE_CMK_BASE
```
