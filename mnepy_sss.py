import paradigm_config as para_cfg
import logging
import mne
import io_helpers as i_o
import preprocessing as preproc
import maxwell_filter_config as sss_cfg
import os
from os.path import join, exists


def handle_erm(info, subject_erm_dir, raw_erm_fname, erm_sss_pattern): # return ERM file locations, directory information
    date_paradigm = i_o.read_measure_date(info)
    subject_erm_date_dir = join(subject_erm_dir, date_paradigm)

    raw_erm = i_o.preload_raws(subject_erm_date_dir, raw_erm_fname) # load the raw ERM data
    erm_sss_fname = i_o.format_variable_names({'date': date_paradigm}, erm_sss_pattern) # ***** check filenaming_config for redundancy
    return raw_erm, erm_sss_fname


def handle_multiple_runs(raws, subject_sss_params, subject_fnames, subject_paradigm_dir):

    sss_list = []
    bads_list = []
    if raws[0].info['dev_head_t'] is None:
        return
    subject_sss_params['destination'] = raws[0].info['dev_head_t'] # use run #1 for head position transformation
    raw_concat = mne.concatenate_raws(raws)
    if len(raw_concat.info['dig']) < 8:
        return
    subject_sss_params['origin'] = preproc.generate_head_origin(raw_concat.info, subject_paradigm_dir,
                                                                  subject_fnames['head_origin'])
    subject_sss_params['head_pos'] = preproc.calc_head_position(raw_concat, subject_fnames['preproc_subdir'],
                                                                  subject_fnames['head_pos'])
    bads_meg = preproc.find_bads_meg(raw_concat, subject_sss_params, subject_fnames['preproc_subdir'],
                                     subject_fnames['meg_bads'], para_cfg.n_jobs)
    raw_concat.info['bads'].extend(bads_meg)
    sss = mne.preprocessing.maxwell_filter(raw_concat, **subject_sss_params)
    sss.save(join(subject_fnames['preproc_subdir'], subject_fnames['sss_paradigm']), overwrite=True)
    return bads_meg


def main(subject, subject_fnames, log):
    logging.basicConfig(filename=log, level=logging.DEBUG)

    subject_paradigm_dir = join(para_cfg.paradigm_dir, subject)
    subject_paradigm_visit_dir = join(subject_paradigm_dir, f"visit_{subject_fnames['meg_date']}")
    subject_erm_dir = join(para_cfg.erm_dir, subject)
    subject_sss_params = sss_cfg.sss_params # load SSS parameters dictionary

    i_o.check_and_build_subdir(subject_fnames['preproc_subdir']) # check and/or build subject subdirectories relevant to the script

    
    if not exists(join(subject_fnames['preproc_subdir'], subject_fnames['sss_paradigm'])):
        raws = i_o.preload_raws(subject_paradigm_visit_dir, subject_fnames['raw_paradigm'])
        bads_list = handle_multiple_runs(raws, subject_sss_params, subject_fnames, subject_paradigm_dir)

    if para_cfg.proc_using_erm:
        raw_erm, erm_sss_fname = handle_erm(raws[0].info, subject_erm_dir, subject_fnames['raw_erm'], subject_fnames['sss_erm'])
        erm_sss = preproc.mne_maxwell_filter_erm(raw_erm, bads_list, subject_sss_params, subject_fnames['preproc_subdir'], erm_sss_fname)
