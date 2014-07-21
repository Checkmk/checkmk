#!/usr/bin/python

import os, sys, uuid

# MSI container to modify
msi_file          = sys.argv[1]
# Version formatted, e.g. 1.2.4.99
new_version_build = "1.0.%s" % sys.argv[2]
# Official version name, e.g 1.2.5i4p1
new_version_name  = sys.argv[3]

new_msi_file = "check_mk_agent.msi"

# Export required idt files into work dir
for entry in [ "File", "Upgrade", "Property" ]:
    print "Export table %s from file %s" % (entry, msi_file)
    os.system("./msiinfo export %(msi_file)s %(property)s > work/%(property)s.idt" % { "msi_file": msi_file, "property": entry })


print "Modify extracted files.."

# ==============================================
# Modify File.idt

# HACK: the 64 bit agent is msi internally handled as check_mk_agent64.exe
os.rename("sources/check_mk_agent-64.exe", "sources/check_mk_agent64.exe")

lines_file_idt = file("work/File.idt").readlines()
file_idt_new   = file("work/File.idt.new", "w")
file_idt_new.write("".join(lines_file_idt[:3]))

for line in lines_file_idt[3:]:
    tokens = line.split("\t")
    filename = tokens[0]
    file_stats = os.stat("sources/%s" % filename)
    new_size    = file_stats.st_size
    tokens[3] = str(new_size)
    # The version of this file is different from the msi installer version !
    tokens[4] = tokens[4] and new_version_build or ""
    tokens[4] = tokens[4] and new_version_build or ""
    file_idt_new.write("\t".join(tokens))
file_idt_new.close()
# ==============================================


# ==============================================
# Modify Upgrade.idt
lines_upgrade_idt = file("work/Upgrade.idt").readlines()
upgrade_idt_new   = file("work/Upgrade.idt.new", "w")
upgrade_idt_new.write("".join(lines_upgrade_idt[:3]))

for idx, token_offset in [ (3, 1), (4, 2) ]:
    new_line = lines_upgrade_idt[idx]
    tokens = new_line.split("\t")
    tokens[token_offset] = new_version_build
    upgrade_idt_new.write("\t".join(tokens))
upgrade_idt_new.close()
# ==============================================


# ==============================================
# Modify Property.idt
product_code = ("{%s}\r\n" % uuid.uuid1()).upper()
upgrade_code = ("{%s}\r\n" % uuid.uuid1()).upper()
lines_property_idt = file("work/Property.idt").readlines()
property_idt_new   = file("work/Property.idt.new", "w")
property_idt_new.write("".join(lines_property_idt[:3]))

for line in lines_property_idt[3:]:
    tokens = line.split("\t")
    if tokens[0] == "ProductName":
        tokens[1] = "Check_MK Agent MSI %s Rev %s\r\n" % (new_version_name, new_version_build.split(".")[-1])
# The upgrade code defines the product family. Do not change it!
#    elif tokens[0] == "UpgradeCode":
#        tokens[1] = upgrade_code
    elif tokens[0] == "ProductCode":
        tokens[1] = product_code
    elif tokens[0] == "ProductVersion":
        tokens[1] = "%s\r\n" % new_version_build
    property_idt_new.write("\t".join(tokens))
property_idt_new.close()
# ==============================================



print "Creating copy of original file %s -> %s" % (msi_file, new_msi_file)

# Make a copy
os.system("cp %(msi_file)s %(new_msi_file)s" % { "msi_file": msi_file, "new_msi_file": new_msi_file})

# Rename modified tables
for entry in [ "Property", "File", "Upgrade" ]:
    os.rename("work/%s.idt.new" % entry , "work/%s.idt" % entry)

for entry in [ "Property", "File", "Upgrade" ]:
    os.system("./msibuild %(new_msi_file)s -i work/%(file)s.idt" %    { "new_msi_file": new_msi_file, "file": entry })

# Update summary info with new uid
package_code = ("{%s}" % uuid.uuid1()).upper()
os.system('./msibuild %(new_msi_file)s -s "Check_MK 32/64 bit MSI installer" "Mathias Kettner GmbH" "Intel;1033" "%(code)s"' %\
        {"code": package_code, "new_msi_file": new_msi_file})

# Remove original product.cab from stream
print "Removing product.cab from %s" % new_msi_file
os.system("./msibuild %(new_msi_file)s -q \"DELETE FROM _Streams where Name = 'product.cab'\"" % { "new_msi_file": new_msi_file } )

# Prepare product.cab file
print "Generating new product.cab"
os.system("lcab -n sources/check_mk.example.ini sources/check_mk_agent.exe sources/check_mk_agent64.exe  work/product.cab ; sync")

# Add modified product.cab
print "Add modified product.cab"
os.system("./msibuild %(new_msi_file)s -a product.cab work/product.cab" % { "new_msi_file": new_msi_file })

print "Successfully created file", new_msi_file



