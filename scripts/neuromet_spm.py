#!/usr/bin/env python3.6

import importlib
import workflows
importlib.reload(workflows)
from ..workflows.NeuroMet_dev_fs7 import NeuroMet as NeuroMet
import os

"""
Version: 0.0.1_alpha : quick&dirty export of notebook in a script 
"""


#ToDo: no global vars should be used
## Paths
raw_data_dir = '/media/drive_s/AG/AG-Floeel-Imaging/00-Rohdaten/02_niftis/NeuroMet_TheresaKoebe/02_NeuroMet'
base_dir = '/media/drive_s/AG/AG-Floeel-Imaging/02-User/NEUROMET'
temp_dir = '/home/WorkFlowTemp/NeuroMet'

#Working directory
w_dir = os.path.join(base_dir, 'Structural_analysis_fs7')

#Excel file with masks
mask_file = '/media/drive_s/AG/AG-Floeel-Imaging/02-User/NEUROMET/Structural_analysis_fs7/List_UNI_DEN_Mask.xlsx'
spm_path='/opt/spm12'
matlab_command = "matlab -nodesktop -nosplash"
fsl_file_format = 'NIFTI_GZ'

qdec_subfolder = ''
cores = 6
overwrite = False
omp_nthreads = 3


def main():
    neuromet_creator = NeuroMet(subject_list, temp_dir, w_dir, omp_nthreads, raw_data_dir, overwrite, spm_path,
                                matlab_command, fsl_file_format, qdec_subjects, qdec_subfolder)
    neuromet_creator.copy_from_raw_data()
    neuromet = neuromet_creator.make_neuromet1_workflow()
    neuromet.run('MultiProc', plugin_args={'n_procs': cores})

if __name__ == "__main__":
    main()