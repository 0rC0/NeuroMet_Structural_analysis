#!/bin/bash

# Usage quantify_hp [NEUROMET Directory]

subdir=$1

#take subject ids
cd $subdir
subs=($(ls -1d NeuroMet*))

#make links
mkdir -p $subdir/qdec/hpquant
cd $subdir/qdec/hpquant

for sub in ${subs[@]}
do
  ln -s $subdir/$sub/${sub}.freesurfer ./${sub}.freesurfer
done

SUBJECTS_DIR=$PWD
quantifyHAsubregions.sh hippoSf T1 ./hp_quantification.csv

exit 0
