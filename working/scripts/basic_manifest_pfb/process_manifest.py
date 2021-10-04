#!/usr/bin/env python3

import argparse
import subprocess
import requests
import json
import sys
import os
import requests
import pandas as pd
import re

# example:
# python process_manifest.py --manifest gdc_manifest.2021-09-28.txt --clinical clinical.tsv --aliquot aliquot.tsv

def main():
    #print ("manifest to PFB script")
    parser = argparse.ArgumentParser(description='Process manifest file.')
    parser.add_argument('--aliquot')
    parser.add_argument('--clinical')
    parser.add_argument('--subject')
    parser.add_argument('--sample')
    parser.add_argument('--gdc')
    parser.add_argument('--gmkf')
    parser.add_argument('--anvil')
    parser.add_argument('--bdcat')
    parser.add_argument('--readgroup')
    parser.add_argument('--demographic')

    args = parser.parse_args()
    aliquot = ""
    clinical = ""
    gdc = ""
    gmkf = ""
    anvil = ""
    bdcat = ""
    sample = ""
    subject = ""
    read_group_df = ""
    aliquot_df = ""
    demographic_df = ""
    if len(sys.argv) == 1:
        parser.print_help()

    # Generic
    if args.aliquot:
        df = pd.read_csv(args.aliquot, sep='\t', header=0)
        aliquot = df

    if args.clinical:
        df = pd.read_csv(args.clinical, sep='\t', header=0)
        clinical = df

    if args.sample:
        df = pd.read_csv(args.sample, sep='\t', header=0)
        sample = df

    if args.subject:
        df = pd.read_csv(args.subject, sep='\t', header=0)
        subject = df

    if args.readgroup:
        df = pd.read_csv(args.readgroup, sep='\t', header=0)
        read_group_df = df

    if args.demographic:
        df = pd.read_csv(args.demographic, sep='\t', header=0)
        demographic_df = df

    # GDC
    # WGS w/ sex, 779 subjects (already filtered in the portal for WGS)
    # python process_manifest.py --gdc gdc/gdc_manifest.2021-09-28.txt --clinical gdc/clinical.tsv --aliquot gdc/aliquot.tsv > gdc_workspace.tsv
    if args.gdc:
        df = pd.read_csv(args.gdc, sep='\t', header=0)
        #print(df.head(10))
        print("entity:gdc_file_id\tfilename\tdrs_uri\tmd5\tsize\tprogram_name\tproject_id\tcase_id\tcase_submitter_id\tsample_id\tsample_submitter_id\tethnicity\trace\tgender")
        for index, row in df.iterrows():
            #print (row[1])
            aliquot_id = extract_uuid(row[1])
            #print("aliquat_id:"+aliquot_id)
            biospecimens = aliquot.loc[aliquot['aliquot_id'] == aliquot_id]
            case_id = str(biospecimens["case_id"].iloc[0])
            project_id = str(biospecimens["project_id"].iloc[0])
            case_submitter_id = str(biospecimens["case_submitter_id"].iloc[0])
            sample_id = str(biospecimens["sample_id"].iloc[0])
            sample_submitter_id = str(biospecimens["sample_submitter_id"].iloc[0])
            #print("case_id: "+case_id)
            case_info = clinical.loc[clinical['case_id'] == case_id]
            ethnicity = str(case_info["ethnicity"].iloc[0])
            race = str(case_info["race"].iloc[0])
            gender = str(case_info["gender"].iloc[0])
            print(row[0]+"\t"+row[1]+"\tdrs://dg.4DFC:"+row[0]+"\t"+str(row[2])+"\t"+str(row[3])+"\tGDC\t"+project_id+"\t"+case_id+"\t"+case_submitter_id+"\t"+sample_id+"\t"+sample_submitter_id+"\t"+ethnicity+"\t"+race+"\t"+gender)
            #aliquot_sub_array = aliquot.loc[aliquot_id, []]
            #filename = row[0]['filename']
            #print(filename)
        gdc = df
    #print(aliquot.head(10))

    # Kids First
    # python process_manifest.py --gmkf gmkf/kidsfirst-participant-family-manifest_2021-09-30.tsv  --clinical gmkf/clinical.tsv > gmkf_workspace.tsv
    if args.gmkf:
        df = pd.read_csv(args.gmkf, sep='\t', header=0)
        print("entity:gmkf_file_id\tfilename\tdrs_uri\tdata_type\tfile_format\tprogram_name\tproject_id\tcase_id\tfamily_id\tsample_submitter_id\taliquot_submitter_id\tethnicity\trace\tgender")
        for index, row in df.iterrows():
            if ((row[4] == "bam" or row[4] == "cram") and (row[5] == 'WGS')):
                file_id = row[1]
                file_submitter_id = row[0]
                filename = row[2]
                drs_uri = "drs://dg.F82A1A:"+row[1]
                data_type = row[3]
                file_format = row[4]
                program_name = 'GMKF'
                project_id = 'phs001228'
                case_id = row[6]
                family_id = row[8]
                sample_submitter_id = row[9]
                aliquot_submitter_id = row[10]
                case_info = clinical.loc[clinical['Participant ID'] == case_id]
                # there's an example of a participant ID mapping to two different cases, the last being incorrect, and I want an example of a mismatch between gender and coverage
                # PT_2GAB5CEY should be male but is labeled as both male and female
                if (len(case_info.index) > 0):
                    ethnicity = str(case_info["Ethnicity"].iloc[0])
                    race = str(case_info["Race"].iloc[0])
                    gender = str(case_info["Gender"].iloc[0])
                    print(file_id+"\t"+filename+"\t"+drs_uri+"\t"+data_type+"\t"+file_format+"\t"+program_name+"\t"+project_id+"\t"+case_id+"\t"+family_id+"\t"+sample_submitter_id+"\t"+aliquot_submitter_id+"\t"+ethnicity+"\t"+race+"\t"+gender)
        gmkf = df

    # AnVIL
    # python process_manifest.py --anvil anvil/sequencing.tsv --subject anvil/subject.tsv --sample anvil/sample.tsv
    if args.anvil:
        df = pd.read_csv(args.anvil, sep='\t', header=0)
        print("entity:anvil_file_id\tfilename\tdrs_uri\tdata_type\tfile_format\tprogram_name\tproject_id\tsample_id\tsample_submitter_id\trace\tgender")
        for index, row in df.iterrows():
            if (row["pfb:experimental_strategy"] == "WGS"):
                file_id = row["entity:sequencing_id"]
                filename = row['pfb:file_name']
                drs_uri = row['pfb:ga4gh_drs_uri']
                data_type = row['pfb:data_type']
                file_format = row['pfb:data_format']
                program_name = 'AnVIL'
                sample_id = row["pfb:sample"]
                sample_info = sample.loc[sample['entity:sample_id'] == sample_id]
                if (len(sample_info.index) > 0):
                    subject_id = sample_info["pfb:subject"].iloc[0]
                    project_id = sample_info["pfb:project_id"].iloc[0]
                    sample_submitter_id = sample_info["pfb:submitter_id"].iloc[0]
                    subject_info = subject.loc[subject['entity:subject_id'] == subject_id]
                    if (len(subject_info.index) > 0):
                        gender = subject_info["pfb:sex"].iloc[0]
                        race = subject_info["pfb:ancestry"].iloc[0]
                        print(file_id+"\t"+filename+"\t"+drs_uri+"\t"+data_type+"\t"+file_format+"\t"+program_name+"\t"+project_id+"\t"+sample_id+"\t"+sample_submitter_id+"\t"+race+"\t"+gender)

    # BioData Catalyst
    # python process_manifest.py --bdcat bdcat/submitted_aligned_reads.tsv --readgroup bdcat/read_group.tsv --aliquot bdcat/aliquot.tsv --sample bdcat/sample.tsv --subject bdcat/subject.tsv --demographic bdcat/demographic.tsv  > bdcat_workspace.tsv
    if args.bdcat:
        df = pd.read_csv(args.bdcat, sep='\t', header=0)
        print("entity:bdcat_file_id\tfilename\tdrs_uri\tdata_type\tfile_format\tprogram_name\tproject_id\tsample_id\tsample_submitter_id\trace\tgender")
        for index, row in df.iterrows():
            experimental_strategy = row['pfb:experimental_strategy']
            if (experimental_strategy == 'WGS'):
                file_id = row["entity:submitted_aligned_reads_id"]
                filename = row['pfb:file_name']
                drs_uri = row['pfb:ga4gh_drs_uri']
                data_type = row['pfb:data_type']
                file_format = row['pfb:data_format']
                program_name = 'BioData Catalyst'
                project_id = row['pfb:project_id']
                read_group = row["pfb:read_group"]
                read_group_info = read_group_df.loc[read_group_df['entity:read_group_id'] == read_group]
                if (len(read_group_info.index) > 0):
                    aliquot_id = read_group_info['pfb:aliquot'].iloc[0]
                    aliquot_info = aliquot.loc[aliquot['entity:aliquot_id'] == aliquot_id]
                    if (len(aliquot_info.index) > 0):
                        sample_id = aliquot_info['pfb:sample'].iloc[0]
                        sample_info = sample.loc[sample['entity:sample_id'] == sample_id]
                        if (len(sample_info.index) > 0):
                            subject_id = sample_info['pfb:subject'].iloc[0]
                            sample_submitter_id = sample_info['pfb:submitter_id'].iloc[0]
                            demographic_info = demographic_df.loc[demographic_df['pfb:subject'] == subject_id]
                            if (len(demographic_info.index) > 0):
                                race = demographic_info["pfb:race"].iloc[0]
                                gender = demographic_info["pfb:annotated_sex"].iloc[0]
                                print(file_id+"\t"+filename+"\t"+drs_uri+"\t"+data_type+"\t"+file_format+"\t"+program_name+"\t"+project_id+"\t"+sample_id+"\t"+sample_submitter_id+"\t"+race+"\t"+gender)

def extract_uuid(uuid):
    regex = re.compile('^([a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})', re.I)
    match = regex.match(uuid)
    return (match.group(1))

if __name__ == '__main__':
    main()
