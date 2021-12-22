# The Dynamics of Mob Programming

## In a nutshell

![dynamics of mob programming][mobprog.svg]

## Before you start:

-   Make sure you have [whatchexec][] installed
-   Checkout the working branch
-   _Use your favorite editor/IDE!_

## When you're the pilot:

-   Start `watchexec`:

```
watchexec -Nnw . -- bash mobprog.sh
```

-   Share your screen
-   Loop over this for a few minutes:
    -   Discuss ideas with the mob
    -   Write some code (tests are code too)
    -   Save your changes (`mobprog.sh` runs and commits and pushes all changes)
-   Unshare your screen
-   Stop `watchexec` and make no further changes until you're the pilot again

## When you're a copilot:

-   Watch the pilot's shared screen
-   Try and be helpful to the pilot
-   Discuss ideas with the mob
-   Resist the temptation to type (wait your turn)

## Once you're done

-   Reorganize the changes by either squashing the commits or creating new ones
-   Don't forget to include other members as [co-authors][] of the commits, e.g.:
    ```
    Co-authored-by: Frank Costello <frank@mob.io>
    Co-authored-by: Tony Montana <tony@mob.io>
    Co-authored-by: Tuco Salamanca <tuco@mob.io>
    ```

[mobprog.svg]: mobprog.svg "The Dynamics of Mob Programming"
[whatchexec]: https://github.com/watchexec/watchexec "Why whatchexec? Because it works on Mac, Linux and Windows ;-)"
[co-authors]: https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors "Creating a commit with multiple authors"
