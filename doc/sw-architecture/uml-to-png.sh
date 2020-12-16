#!/bin/bash
OUTPUT_DIR="./output/"

docker build --tag plantuml .

uml_files=$(ls *.puml)

for uml_file in ${uml_files}
do
   :
   echo "Creating png from $uml_file"
   cat "$uml_file" | docker run --rm -i plantuml:latest -tpng > $OUTPUT_DIR${uml_file/.puml/.png}
done

