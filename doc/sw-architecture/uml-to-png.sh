#!/bin/bash

docker build --tag plantuml .
docker run -t -v "$PWD":"$PWD" -w "$PWD" plantuml:latest java -Djava.awt.headless=true -jar /plantuml.jar *.puml -o output/
