# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""Interfaces to assorted Freesurfer utility programs.
"""
import os
import re
import shutil

from nipype import logging
from nipype.utils.filemanip import fname_presuffix, split_filename

from nipype import logging, LooseVersion
from nipype.utils.filemanip import fname_presuffix, check_depends
from nipype.interfaces.io import FreeSurferSource

from nipype.interfaces.base import (
    TraitedSpec,
    File,
    traits,
    Directory,
    InputMultiPath,
    OutputMultiPath,
    CommandLine,
    CommandLineInputSpec,
    isdefined,
)

from nipype.interfaces.freesurfer.base import FSCommand, FSTraitedSpec, FSTraitedSpecOpenMP, FSCommandOpenMP, Info
from nipype.interfaces.freesurfer.utils import copy2subjdir

__docformat__ = "restructuredtext"
iflogger = logging.getLogger("nipype.interface")

# Keeping this to avoid breaking external programs that depend on it, but
# this should not be used internally
FSVersion = Info.looseversion().vstring

class SegmentHA_T1InputSpec(FSTraitedSpec):
    """
    from: https://surfer.nmr.mgh.harvard.edu/fswiki/HippocampalSubfieldsAndNucleiOfAmygdala
        Using only the T1 scan from recon-all

    To analyze your subject "bert", you would simply type:
    """
    # subject_dir heredited by
    subject_id = traits.String(
        mandatory=True, argstr="%s", desc="subject id of surface file"
    )
    subjects_dir = traits.String(
        mandatory=True, argstr="%s", desc="subject dir of surface file"
    )



class SegmentHA_T1OutputSpec(FSTraitedSpec):
    """
    """
    subjects_dir = Directory(exists=True, desc="Freesurfer subjects directory.")
    subject_id = traits.Str(desc="Subject name for whom to retrieve data")

class SegmentHA_T1(FSCommand):
    """
    ToDo : Check version, should be >= 7
         : log should be not at INFO level
    Example Usage:
    > import nipype.interfaces.freesurfer as fs
    > from fssegmentHA_T1 import SegmentHA_T1
    > segment_ha = SegmentHA_T1()
    > segment_ha.inputs.subjects_dir = '/media/drive_s/AG/AG-Floeel-Imaging/02-User/NEUROMET/test_freesurfer_7/Structural_analysis/workflows'
    > segment_ha.inputs.subject_id = 'recon_all_test'
    > segment_ha.cmdline
    > segment_ha.run()
    """
    _cmd = "segmentHA_T1.sh"
    input_spec = SegmentHA_T1InputSpec
    output_spec = SegmentHA_T1OutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["subjects_dir"] = self.inputs.subjects_dir
        outputs["subject_id"] = self.inputs.subject_id