# Add hash SHA-256 to a file
# args[0] file to be hashed
# args[1] file for output
# format of line <file_name> <hash>
#
# The resulting file is need for installer
#
# 2023 (c) Checkmk GmbH
#

$file_to_hash = $args[0]
$out_file = $args[1]

$file_to_hash_name = Get-ChildItem -Path $file_to_hash | Select-Object Name -ExpandProperty Name
Add-Content -Path $out_file -Value ($file_to_hash_name + " ") -NoNewLine
Get-FileHash $file_to_hash -Algorithm SHA256 | Select-Object Hash -ExpandProperty Hash | Add-Content -Path $out_file