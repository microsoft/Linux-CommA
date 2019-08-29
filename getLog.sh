#!/bin/bash
currDir=$(pwd)
echo "Current WOrking directory: $currDir"
cd ../linux
git pull
input="$currDir/hyperVfiles.txt"
cnt=0
while IFS= read -r line
do
  echo "$line"
  git log -p -- $line >> "../commit-log/$cnt.log"
  ((cnt++))
done < "$input"
