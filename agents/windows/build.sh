# bash script library for building an autotools project for 32 / 64 bit MinGW
# target architectures.
#
# Usage: source this library to your script.

# function parse-args:
# Parse the number N of parallel build jobs from option -jN to variable njobs
# and optional build targets to variable targets. If option -jN is not given,
# njobs defaults to the half of available CPU cores.
function parse-args {
    while getopts "j:" arg ; do
        case $arg in
            j)
                njobs=${OPTARG}
                ;;
            *)
                exit 1
                ;;
        esac
    done

    shift $((OPTIND-1))

    [ "$1" = "--" ] && shift
    targets="$@" # no parameter -> default make target

    # If njobs is not set, use half of available CPU cores.
    [[ -n $njobs ]] || njobs=$(($(grep -c processor /proc/cpuinfo)/2))
    [[ $njobs -le 0 ]] && njobs=1 # Ensure one core after arithmetic division.
    :
}

# Build architecture configuration:
common=-w64-mingw32 # common part of all MinGW binaries
declare -A builddirs archs tranforrms
builddirs=([32]=build [64]=build64) # build directories for 32 and 64 bit
archs=([32]=i686 [64]=x86_64) # target architectures for 32 and 64 bit
transforms=([32]=s/// [64]=s/$/-64/g) # sed expr's for transforming 32 and 64 bit exe's

# function build:
# The build steps to be repeated for each target architecture (Win 32 and 64).
#
# Dependencies: the sourcing script must define the variable njobs (number of
# parallel build jobs). The variable targets can be used for specifying desired
# make target(s) to be executed. These variables can be parsed using the
# parse-args function
#
# param $1 : the architecture  - 32 or 64
function build {
    mkdir -p ${builddirs[$1]}
    cd ${builddirs[$1]}
    # options and variables for 'configure':
    # --bindir : target install dir
    # --program-transform-name : sed expression for renaming binary executable
    #                            during install step
    # --build : architecture of build machine (for cross-compilation)
    # --host : target architecture of cross-compilation
    # CC : C compiler (redundant but quiets a cross-compilation warning)
    # CXX : C++ compiler
    # WINDRES : program for manipulating Windows resource files
    # STRIP : program for stripping debugging symbols
    ../configure --bindir=$(dirname $(pwd)) \
                 --program-transform-name=${transforms[$1]} \
                 --build i686-pc-linux-gnu \
                 --host ${archs[$1]}${common} \
                 CC=${archs[$1]}${common}-gcc-posix \
                 CXX=${archs[$1]}${common}-g++-posix \
                 WINDRES=${archs[$1]}${common}-windres \
                 STRIP=${archs[$1]}${common}-strip

    # Default (no targets given): do parallel build and install non-debug exe's.
    if [ -z "$targets" ] ; then
        make -j${njobs} && make install-strip
    else
        # If special targets given, do just them.
        make -j${njobs} "$targets"
    fi
    cd -
}
