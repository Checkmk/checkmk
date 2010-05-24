#!/usr/bin/python
import pprint, tarfile

pac_ext = ".mkp"

class PackageException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

pac_dir = var_dir + "/packages/"
try:
    os.makedirs(pac_dir)
except:
    pass

package_parts = [
  ( "checks",   "Checks",               checks_dir ),
  ( "checkman", "Checks' man pages",    check_manpages_dir ),
  ( "agents",   "Agents",               agents_dir ),
  ( "web",      "Multisite extensions", web_dir ),
]

def do_packaging(command, args):
    commands = {
        "create" : package_create,
        "list"   : package_list,
        "pack"   : package_pack,
    }
    f = commands.get(command)
    if f:
        try:
            f(args)
        except PackageException, e:
            sys.stderr.write("%s\n" % e)
            sys.exit(1)
    else:
        sys.stderr.write("Invalid packaging command. Allowed are: %s.\n" % 
                ", ".join(commands.keys()))
        sys.exit(1)
    
def package_list(args):
    table = []
    for pacname in all_packages():
        package = read_package(pacname)
        table.append((pacname, package["title"], package["num_files"]))
    print_table(["Name", "Title", "Files"], [ tty_green, tty_yellow, tty_cyan ], table)

def package_create(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = args[0]
    if read_package(pacname):
        raise PackageException("Package %s already existing." % pacname)

    verbose("Creating new package %s\n" % pacname)
    filelists = {}
    package = {
        "title"           : "Title of %s" % pacname,
        "description"     : "Please add a description here",
        "version"         : "1.0",
        "author"          : "Add your name here",
        "download_url"    : "http://example.com/%s/" % pacname,
        "files"           : filelists
    }
    num_files = 0
    for part, title, dir in package_parts:
        verbose("  Unpackaged files in %s:\n" % dir) 
        files = unpackaged_files_in_dir(part, dir)
        for f in files:
            verbose("    %s\n" % f)
        filelists[part] = files
        num_files += len(files)

    write_package(pacname, package)
    verbose("New package %s created with %d files.\n" % (pacname, num_files))

def package_pack(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    pacname = args[0]
    package = read_package(pacname)
    if not package:
        raise PackageException("Package %s not existing or corrupt." % pacname)
    tarfilename = pacname + pac_ext
    verbose("Packing %s => %s...\n" % (pacname, tarfilename))

    def create_info(filename, size):
        info = tarfile.TarInfo("info")
        info.mtime = time.time()
        info.uid = 0
        info.gid = 0
        info.size = size
        info.mode = 0644
        info.type = tarfile.REGTYPE
        info.name = filename
        return info
    
    tar = tarfile.open(tarfilename, "w:gz")
    info_file = fake_file(pprint.pformat(package)) 
    info = create_info("info", info_file.size())
    tar.addfile(info, info_file)

    # Now pack the actual files into sub tars
    for part, title, dir in package_parts:
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            subtarname = part + ".tar"
            subdata = os.popen("tar cf - --dereference --force-local -C '%s' %s" % (dir, " ".join(filenames))).read()
            info = create_info(subtarname, len(subdata))
            tar.addfile(info, fake_file(subdata))

    tar.close()

    verbose("Successfully created %s\n" % tarfilename)


# Und jetzt wie bei --backup arbeiten mit dem in Python eingebauten tar...

def files_in_dir(dir, prefix = ""):
    result = []
    files = os.listdir(dir)
    for f in files:
        if f in [ '.', '..' ] or f.startswith('.') or f.endswith('~'):
            continue
        path = dir + "/" + f
        if os.path.isdir(path):
            result += files_in_dir(path, prefix + f + "/")
        else:
            result.append(prefix + f)
    result.sort()
    return result

def unpackaged_files_in_dir(part, dir):
    all    = files_in_dir(dir)
    packed = packaged_files_in_dir(part)
    return [ f for f in all if f not in packed ]

def packaged_files_in_dir(part):
    result = []
    for pacname in all_packages():
        package = read_package(pacname)
        result += package["files"].get(part, [])
    return result
   
def read_package(pacname):
    try:
        package = eval(file(pac_dir + pacname).read())
        num_files = sum([len(fl) for fl in package["files"].values() ])
        package["num_files"] = num_files
        return package
    except IOError:
        return None

def write_package(pacname, package):
    file(pac_dir + pacname, "w").write(pprint.pformat(package) + "\n")

def all_packages():
    all = [ p for p in os.listdir(pac_dir) if p not in [ '.', '..' ] ]
    all.sort()
    return all


