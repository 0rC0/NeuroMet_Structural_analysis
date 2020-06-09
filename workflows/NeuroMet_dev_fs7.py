from nipype.pipeline.engine import Workflow, Node, MapNode
from nipype import DataGrabber, DataSink, IdentityInterface
import nipype.interfaces.fsl as fsl
import \
    nipype.interfaces.freesurfer as fs
import nipype.interfaces.spm as spm
import nipype.interfaces.matlab as mlab
import os
from nipype.interfaces.utility import Function
from nipype.algorithms.misc import Gunzip
import shutil
import glob
from workflows.fssegmentHA_T1 import SegmentHA_T1 # freesurfer 7 hippocampus segmentation

__author__ = "Andrea Dell'Orco"
__version__ = "1.2.0_fs7"
__maintainer__ = "Andrea Dell'Orco"
__email__ = "andrea.dellorco@charite.de"
__status__ = "Development"


class NeuroMet():

    def __init__(self, subject_list, temp_dir, w_dir, omp_nthreads, raw_data_dir, overwrite, spm_path,
                 matlab_command, fsl_file_format, qdec_subjects, qdec_subfolder):

        self.subject_list = subject_list
        self.raw_data_dir = raw_data_dir
        self.temp_dir = temp_dir
        self.w_dir = w_dir
        self.omp_nthreads = omp_nthreads
        self.overwrite = overwrite
        self.spm_path = spm_path
        self.matlab_command = matlab_command
        self.fsl_file_format = fsl_file_format
        self.qdec_subjects = qdec_subjects
        self.qdec_subfolder = qdec_subfolder

        self.subject_prefix = 'NeuroMet'
        self.mask_suffix = '.SPMbrain_bin.nii.gz'
        self.mask_file = '/media/drive_s/AG/AG-Floeel-Imaging/02-User/NEUROMET/Structural_analysis_fs7/List_UNI_DEN_Mask.xlsx'

        mlab.MatlabCommand.set_default_matlab_cmd(matlab_command)
        mlab.MatlabCommand.set_default_paths(spm_path)
        fsl.FSLCommand.set_default_output_type(fsl_file_format)  # fsl output format

    def copy_from_raw_data(self):

        for sub_num in self.subject_list:
            sub = self.subject_prefix + sub_num
            print('Copying {0}'.format(sub))
            den = glob.glob(self.raw_data_dir + '/{0}/*UNI_DEN*/*.nii.gz'.format(sub))[0]  # should be only 1 file
            uni = glob.glob(self.raw_data_dir + '/{0}/*UNI_Images*/*.nii.gz'.format(sub))[0]  # should be only 1 file
            sub_dest_dir = os.path.join(self.w_dir, sub)
            if not os.path.isdir(sub_dest_dir):
                os.makedirs(sub_dest_dir)
            uni_name = sub + '.UNI_mp2rage_orig.nii.gz'
            den_name = sub + '.DEN_mp2rage_orig.nii.gz'
            if not os.path.isfile(os.path.join(sub_dest_dir, uni_name)) or self.overwrite:
                shutil.copyfile(uni, os.path.join(sub_dest_dir, uni_name))
                print('{0} copyed to {1}'.format(uni, os.path.join(sub_dest_dir, uni_name)))
            else:
                print('File exists, Skipping copy')
            if not os.path.isfile(os.path.join(sub_dest_dir, den_name)) or self.overwrite:
                shutil.copyfile(den, os.path.join(sub_dest_dir, den_name))
                print('{0} copyed to {1}'.format(den, os.path.join(sub_dest_dir, den_name)))
            else:
                print('File exists, Skipping copy')


    # Ref: http://nipype.readthedocs.io/en/latest/users/function_interface.html
    def copy_mask(in_file, fs_dir):
        """
        Copy an user modified mask to freesurfer folder

        in_file has to be connected with out_file from mri_mask
        fs_dir has to be connected with subjects_dir from fs_recon2,

        return fs_dir for recon2
        """
        import os
        import shutil

        out_file = os.path.join(fs_dir, 'recon_all/mri/brainmask.mgz')
        bk_file = os.path.join(fs_dir, 'recon_all/mri/brainmask_false.mgz')
        shutil.copy(out_file, bk_file)
        shutil.copy(in_file, out_file)

        return fs_dir


    def copy_freesurfer_dir(in_dir, sub_id, out_dir):
        """
        Copy the recon_all folder to subject dir as Subject_id.freesurfer
        """
        import os
        import shutil
        # mkdir NeuroMet034.freesurfer &&
        # curdir=$PWD && cd /home/WorkFlowTemp/NeuroMet/Neuromet2/FreeSurfer/_subject_id_034/fs_recon1 &&
        # tar -hcf - ./recon_all | tar -xf - -C $curdir && cd $curdir && mv recon_all NeuroMet034.freesurfer
        shutil.copytree(os.path.join(in_dir, 'recon_all'),
                           os.path.join(out_dir, 'NeuroMet{0}/NeuroMet{0}.freesurfer'.format(sub_id)))
        return out_dir


    def sublist(in_list, start=0, end=3):
        """
        Return a sublist of a given list
        """
        return in_list[start:end]


    def spm_tissues(in_list):
        """
        from a SPM NewSegment Tissues list, return GM, WM and CSf
        """
        return in_list[0][0], in_list[1][0], in_list[2][0]


    def gzip_spm(in_list):
        """
        gzip SPM native_tissues list
        SPM returns a list of lists [[file1], [file2],.....]
        """
        from os import system
        from os.path import isfile
        out_list = []
        for l in in_list:
            in_file = l[0]
            if isfile(in_file):
                cmdline = 'gzip -9 {0}'.format(in_file)
                system(cmdline)
                out_file = in_file + '.gz'
                out_list.append(list([out_file]))
            elif isfile(in_file + '.gz'):
                out_file = in_file + '.gz'
                out_list.append(list([out_file]))
        return out_list


    def make_infosource(self):

        # Infosource: Iterate through subject names
        infosource = Node(interface=IdentityInterface(fields=['subject_id']), name="infosource")

        infosource.iterables = ('subject_id', self.subject_list)
        return infosource


    def make_sink(self):
        sink = Node(interface=DataSink(),
                    name='sink')
        sink.inputs.base_directory = self.w_dir
        sink.inputs.substitutions = [('_subject_id_',self.subject_prefix),
                                     ('DEN_mp2rage_orig_reoriented_masked_maths', 'mUNIbrain_DENskull_SPMmasked'),
                                     ('_mp2rage_orig_reoriented_maths_maths_bin', '_brain_bin')]
        sink.inputs.regexp_substitutions = [(r'c1NeuroMet(.*).UNI_brain_bin.nii.gz', r'NeuroMet\1.UNI_brain_bin.nii.gz'),
        (r'c1NeuroMet(.*).DEN_brain_bin.nii.gz', r'NeuroMet\1.DEN_brain_bin.nii.gz')]
        return sink


    def make_segment_uni(self):
        # Ref: http://nipype.readthedocs.io/en/0.12.1/interfaces/generated/nipype.interfaces.fsl.utils.html#reorient2std
        ro_uni = Node(interface=fsl.Reorient2Std(), name='ro')

        # Ref: http://nipype.readthedocs.io/en/latest/interfaces/generated/interfaces.spm/preprocess.html#segment
        seg_uni = Node(interface=spm.NewSegment(channel_info=(0.0001, 60, (True, True))),
                       name="seg_uni")

        spm_tissues_split_uni = Node(
            Function(['in_list'], ['gm', 'wm', 'csf'], self.spm_tissues),
            name='spm_tissues_split_uni')

        gzip_uni = Node(Function(['in_list'], ['out_list'], self.gzip_spm),
                        name='gzip_uni')

        segment_uni = Workflow(name='Segment_uni', base_dir=self.temp_dir)

        gunzip_uni = Node(interface=Gunzip(), name='gunzip_uni')
        # for new segment
        segment_uni.connect(ro_uni, 'out_file', gunzip_uni, 'in_file')
        segment_uni.connect(gunzip_uni, 'out_file', seg_uni, 'channel_files')
        segment_uni.connect(seg_uni, 'native_class_images', spm_tissues_split_uni, 'in_list')
        return segment_uni


    def make_segment_den(self):
        # Ref: http://nipype.readthedocs.io/en/0.12.1/interfaces/generated/nipype.interfaces.fsl.utils.html#reorient2std
        ro_den = Node(interface=fsl.Reorient2Std(), name='ro')

        # Ref: http://nipype.readthedocs.io/en/latest/interfaces/generated/interfaces.spm/preprocess.html#segment
        seg_den = Node(interface=spm.NewSegment(channel_info=(0.0001, 60, (True, True))),
                       name="seg_den")

        spm_tissues_split_den = Node(
            Function(['in_list'], ['gm', 'wm', 'csf'], self.spm_tissues),
            name='spm_tissues_split_den')

        gzip_den = Node(Function(['in_list'], ['out_list'], self.gzip_spm),
                        name='gzip_den')
        gunzip_den = Node(interface=Gunzip(), name='gunzip_den')
        segment_den = Workflow(name='Segment_den', base_dir=self.temp_dir)

        # for new segment
        segment_den.connect(ro_den, 'out_file', gunzip_den, 'in_file')
        segment_den.connect(gunzip_den, 'out_file', seg_den, 'channel_files')
        segment_den.connect(seg_den, 'native_class_images', spm_tissues_split_den, 'in_list')
        return segment_den


    def make_mask_uni(self):
        # The c2 and c3 images from SPM Segment are added to c1 to generate a mask
        mask_uni = Workflow(name='Mask_UNI', base_dir=self.temp_dir)
        sum_tissues_uni1 = Node(interface=fsl.maths.MultiImageMaths(op_string=' -add %s'),
                                name='sum_tissues1')
        sum_tissues_uni2 = Node(interface=fsl.maths.MultiImageMaths(op_string=' -add %s'),
                                name='sum_tissues2')
        gen_mask_uni = Node(interface=fsl.maths.UnaryMaths(operation='bin'),
                            name='gen_mask')
        mask_uni.connect(sum_tissues_uni1, 'out_file', sum_tissues_uni2, 'in_file')
        mask_uni.connect(sum_tissues_uni2, 'out_file', gen_mask_uni, 'in_file')
        return mask_uni


    def make_mask_den(self):
        # The c2 and c3 images from SPM Segment are added to c1 to generate a mask
        mask_den = Workflow(name='Mask_DEN', base_dir=self.temp_dir)
        sum_tissues_den1 = Node(interface=fsl.maths.MultiImageMaths(op_string=' -add %s'),
                                name='sum_tissues1')
        sum_tissues_den2 = Node(interface=fsl.maths.MultiImageMaths(op_string=' -add %s'),
                                name='sum_tissues2')
        gen_mask_den = Node(interface=fsl.maths.UnaryMaths(operation='bin'),
                            name='gen_mask')
        mask_den.connect(sum_tissues_den1, 'out_file', sum_tissues_den2, 'in_file')
        mask_den.connect(sum_tissues_den2, 'out_file', gen_mask_den, 'in_file')
        return mask_den


    def make_neuromet1_workflow(self):

        infosource = self.make_infosource()

        info = dict(
            uni=[['subject_id', 'subject_id', 'UNI']],
            den=[['subject_id', 'subject_id', 'DEN']])

        datasource = Node(
            interface=DataGrabber(
                infields=['subject_id'], outfields=['uni', 'den']),
            name='datasource')
        datasource.inputs.base_directory = self.w_dir
        datasource.inputs.template = 'NeuroMet%s/NeuroMet%s.%s_mp2rage_orig.nii.gz'
        datasource.inputs.template_args = info
        datasource.inputs.sort_filelist = False

        sink = self.make_sink()

        segment_uni = self.make_segment_uni()

        segment_den = self.make_segment_den()

        mask_uni = self.make_mask_uni()

        mask_den = self.make_mask_den()

        neuromet = Workflow(name='NeuroMet', base_dir=self.temp_dir)
        neuromet.connect(infosource, 'subject_id', datasource, 'subject_id')
        neuromet.connect(datasource, 'uni', segment_uni, 'ro.in_file')
        neuromet.connect(datasource, 'den', segment_den, 'ro.in_file')

        # neuromet.connect()
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.gm', mask_uni, 'sum_tissues1.in_file')
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.wm', mask_uni, 'sum_tissues1.operand_files')
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.csf', mask_uni, 'sum_tissues2.operand_files')
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.gm', sink, '@gm_uni')
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.wm', sink, '@wm_uni')
        neuromet.connect(segment_uni, 'spm_tissues_split_uni.csf', sink, '@csf_uni')
        neuromet.connect(segment_uni, 'seg_uni.bias_corrected_images', sink, '@biascorr_uni')

        neuromet.connect(segment_den, 'spm_tissues_split_den.gm', mask_den, 'sum_tissues1.in_file')
        neuromet.connect(segment_den, 'spm_tissues_split_den.wm', mask_den, 'sum_tissues1.operand_files')
        neuromet.connect(segment_den, 'spm_tissues_split_den.csf', mask_den, 'sum_tissues2.operand_files')
        neuromet.connect(segment_den, 'spm_tissues_split_den.gm', sink, '@gm_den')
        neuromet.connect(segment_den, 'spm_tissues_split_den.wm', sink, '@wm_den')
        neuromet.connect(segment_den, 'spm_tissues_split_den.csf', sink, '@csf_den')
        neuromet.connect(segment_den, 'seg_den.bias_corrected_images', sink, '@biascorr_den')

        # neuromet.connect(comb_imgs, 'uni_brain_den_surr_add.out_file', sink, '@img')
        neuromet.connect(mask_uni, 'gen_mask.out_file', sink, '@mask_uni')
        neuromet.connect(mask_den, 'gen_mask.out_file', sink, '@mask_den')
        neuromet.connect(segment_den, 'ro.out_file', sink, '@ro_den')
        # neuromet.connect(segment_uni, 'ro.out_file', sink, '@ro_uni')

        return neuromet


    def make_comb_imgs(self):
        #Ref: http://nipype.readthedocs.io/en/1.0.4/interfaces/generated/interfaces.fsl/maths.html
        mask_uni_bias = Node(interface=fsl.maths.ApplyMask(),
                             name = 'mask_uni_bias')
        uni_brain_den_surr_bin = Node(interface=fsl.maths.UnaryMaths(operation = 'binv'),
                                      name = 'uni_brain_den_surr_bin')
        uni_brain_den_surr_mas = Node(interface=fsl.maths.ApplyMask(),
                                      name = 'uni_brain_den_surr_mas')
        uni_brain_den_surr_add = Node(interface=fsl.maths.BinaryMaths(operation = 'add'),
                           name = 'uni_brain_den_surr_add')

        comb_imgs = Workflow(name='CombinedImages', base_dir=self.temp_dir)
        comb_imgs.connect(mask_uni_bias, 'out_file', uni_brain_den_surr_bin, 'in_file')
        comb_imgs.connect(uni_brain_den_surr_bin, 'out_file', uni_brain_den_surr_mas, 'mask_file')
        comb_imgs.connect(uni_brain_den_surr_mas, 'out_file', uni_brain_den_surr_add, 'in_file')
        comb_imgs.connect(mask_uni_bias, 'out_file', uni_brain_den_surr_add, 'operand_file')
        return comb_imgs

    def make_freesurfer(self):

        # Ref: http://nipype.readthedocs.io/en/1.0.4/interfaces/generated/interfaces.freesurfer/preprocess.html#reconall
        fs_recon1 = Node(interface=fs.ReconAll(directive='autorecon1',
                                               mris_inflate='-n 15',
                                               hires=True,
                                               mprage=True,
                                               openmp=self.omp_nthreads),
                         name='fs_recon1',
                         n_procs=self.omp_nthreads)
        fs_mriconv = Node(interface=fs.MRIConvert(out_type='mgz'),
                          name='fs_mriconv')
        fs_vol2vol = Node(interface=fs.ApplyVolTransform(mni_152_reg=True),
                          name='fs_vol2vol')
        fs_mrimask = Node(interface=fs.ApplyMask(), name='fs_mrimask')
        fs_recon2 = Node(interface=fs.ReconAll(directive='autorecon2',
                                               hires=True,
                                               mprage=True,
                                               hippocampal_subfields_T1=False,
                                               openmp=self.omp_nthreads),
                         name='fs_recon2',
                         n_procs=self.omp_nthreads)
        #2020.05 Hippocampal subfield is a separate script in Freesurfer 7
        fs_recon3 = Node(interface=fs.ReconAll(directive='autorecon3',
                                               hires=True,
                                               mprage=True,
                                               hippocampal_subfields_T1=False,
                                               openmp=self.omp_nthreads),
                         name='fs_recon3',
                         n_procs=self.omp_nthreads)

        copy_brainmask = Node(
            Function(['in_file', 'fs_dir'], ['fs_dir'], self.copy_mask),
            name='copy_brainmask')
        segment_hp = Node(interface=SegmentHA_T1(), name='segment_hp')

        freesurfer = Workflow(name='FreeSurfer', base_dir=self.temp_dir)
        freesurfer.connect(fs_recon1, 'T1', fs_vol2vol, 'target_file')
        freesurfer.connect(fs_mriconv, 'out_file', fs_vol2vol, 'source_file')
        freesurfer.connect(fs_recon1, 'T1', fs_mrimask, 'in_file')
        freesurfer.connect(fs_vol2vol, 'transformed_file', fs_mrimask, 'mask_file')
        freesurfer.connect(fs_mrimask, 'out_file', copy_brainmask, 'in_file')
        freesurfer.connect(fs_recon1, 'subjects_dir', copy_brainmask, 'fs_dir')
        freesurfer.connect(copy_brainmask, 'fs_dir', fs_recon2, 'subjects_dir')
        freesurfer.connect(fs_recon2, 'subjects_dir', fs_recon3, 'subjects_dir')
        freesurfer.connect(fs_recon3, 'subjects_dir', segment_hp, 'subjects_dir')
        return freesurfer

    def get_mask_name(subject_id):
        import pandas as pd
        # ToDo: correct this hard-coded mask_file
        # TypeError: get_mask_name() missing 1 required positional argument: 'self
        mask_file = '/media/drive_s/AG/AG-Floeel-Imaging/02-User/NEUROMET/Structural_analysis_fs7/List_UNI_DEN_Mask.xlsx'
        df = pd.read_excel(mask_file, header=None, names=['ids', 'masks', 'note'])
        d = dict(zip(df.ids.values, df.masks.values))
        return d['NeuroMET' + subject_id]

    def make_neuromet2_workflow(self):

        infosource = self.make_infosource()

        mask_source = Node(interface=Function(['mask_file', 'subject_id'], ['mask'], self.get_mask_name),
                           name='get_mask')
        # Datasource: Build subjects' filenames from IDs
        info = dict(
            mask = [['subject_id', '', 'subject_id', 'mask', '_brain_bin.nii.gz']],
            uni_bias_corr = [['subject_id', 'm', 'subject_id', '', 'UNI_mp2rage_orig_reoriented.nii']],
            den_ro = [['subject_id', '', 'subject_id', '', 'DEN_mp2rage_orig_reoriented.nii.gz']])

        datasource = Node(
            interface=DataGrabber(
                infields=['subject_id', 'mask'], outfields=['mask', 'uni_bias_corr', 'den_ro']),
            name='datasource')
        datasource.inputs.base_directory = self.w_dir
        datasource.inputs.template = 'NeuroMet%s/%sNeuroMet%s.%s%s'
        datasource.inputs.template_args = info
        datasource.inputs.sort_filelist = False

        sink = self.make_sink()

        comb_imgs = self.make_comb_imgs()

        freesurfer = self.make_freesurfer()

        neuromet2 = Workflow(name='Neuromet2', base_dir=self.temp_dir)
        neuromet2.connect(infosource, 'subject_id', datasource, 'subject_id')
        neuromet2.connect(infosource, 'subject_id', mask_source, 'subject_id')
        neuromet2.connect(mask_source, 'mask', datasource, 'mask')
        neuromet2.connect(datasource, 'uni_bias_corr', comb_imgs, 'mask_uni_bias.in_file')
        neuromet2.connect(datasource, 'mask', comb_imgs, 'mask_uni_bias.mask_file')
        neuromet2.connect(datasource, 'den_ro', comb_imgs, 'uni_brain_den_surr_mas.in_file')

        neuromet2.connect(comb_imgs, 'uni_brain_den_surr_add.out_file', freesurfer, 'fs_recon1.T1_files')
        neuromet2.connect(datasource, 'mask', freesurfer, 'fs_mriconv.in_file')

        out_dir_source = Node(interface=IdentityInterface(fields=['out_dir'], mandatory_inputs=True), name = 'out_dir_source')
        out_dir_source.inputs.out_dir = self.w_dir

        copy_freesurfer_dir = Node(
            Function(['in_dir', 'sub_id', 'out_dir'], ['out_dir'], self.copy_freesurfer_dir),
            name='copy_freesurfer_dir')


        neuromet2.connect(comb_imgs, 'uni_brain_den_surr_add.out_file', sink, '@img')
        neuromet2.connect(infosource, 'subject_id', copy_freesurfer_dir, 'sub_id')
        neuromet2.connect(freesurfer, 'segment_hp.subjects_dir', copy_freesurfer_dir, 'in_dir')
        neuromet2.connect(out_dir_source, 'out_dir', copy_freesurfer_dir, 'out_dir')

        return neuromet2


    def generate_qdec_file(self):

        qdec_dir = os.path.join(self.w_dir, self.qdec_subfolder)
        if not os.path.isdir(qdec_dir):
            os.mkdir(qdec_dir)
        if self.qdec_subjects == []:
            fs_dirs = glob.glob(self.w_dir + '/NeuroMet[0-9][0-9][0-9]/NeuroMet[0-9][0-9][0-9].freesurfer')
        else:
            fs_dirs = [(self.w_dir + '/NeuroMet{0}/NeuroMet{0}.freesurfer'.format(f)) for f in self.qdec_subjects]
        subdirs_list = []
        for d in fs_dirs:
            subdirs_list.append('/'.join(d.split('/')[-2:]))
        qdec_filename = os.path.join(qdec_dir, 'Freesurfer_qdec_NeuroMet.dat')
        with open(qdec_filename, 'w') as f:
            f.write('SUBJECTS_DIR {0} \n'.format(self.w_dir))
            f.write('fsid    factor\n')
            for d in subdirs_list:
                f.write('{0}\t1\n'.format(d))
        return qdec_dir, subdirs_list, qdec_filename

    def cat_file(self, filename):

        s = ''
        with open(filename, 'r') as f:
            for row in f:
                s = s + '\n' + row
        return s

    def show_qdec_stuff(self):

        qdec_dir, subdirs_list, qdec_filename = self.generate_qdec_file()
        s = '''qdec directory : {0} \n\n subjects: {1} \n\n qdec file: \n {2}
        '''.format(qdec_dir, '\n'.join(subdirs_list), self.cat_file(qdec_filename))
        return s

    def check_gz_masks(self, subject_list):
        """
        check in the subject path if a file $Subject.SPMbrain_bin.nii.gz exists.

        If the .nii exists, compress it
        If neither the .nii.gz nor the .nii, return print a message
        """
        import gzip
        import shutil
        counter = 0
        for sub in self.subject_list:
            subject = self.subject_prefix + sub
            mask_file = os.path.join(self.w_dir, subject, subject + self.mask_suffix)
            # Check if the mask file exists and is in .nii.gz format
            if not os.path.isfile(mask_file):
                # if not, check if a .nii file exists
                if os.path.isfile(mask_file.strip('.gz')):
                    # if exists, compress it with gzip
                    with open(mask_file.strip('.gz'), 'rb') as f_in:
                        with gzip.open(mask_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                            print('{0} compressed'.format(subject))
                else:
                    counter += 1
                    print('No mask for subject {0}'.format(subject))
        print('{0} Subjects without mask'.format(counter))