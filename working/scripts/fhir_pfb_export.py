# Given a FHIR server and auth token, this script runs a query, iterates through the matching patient results, and generates a PFB for the patients.

import requests
import sys
import json
import urllib3
import subprocess
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fhir_server = sys.argv[1]
token = sys.argv[2]
condition = sys.argv[3]

headers = {"Authorization": "Bearer " + token}

def get_response_json_object(url):
	r = requests.get(url, headers=headers, verify=False)
	#print("URL: "+url)
	#print("RESPONSE: "+str(r.json()))
	return r.json()

resource_types=[]
patient_uris = []
count = 0;
json_obj = get_response_json_object(fhir_server + '/Condition?_count=25&code:text=' + condition)
#print(json_obj)
#exit()
if ('entry' in json_obj):
	for entry in json_obj['entry']:
		patient_uri = entry['resource']['subject']['reference']
		print('Found matching patient:', patient_uri)
		patient_uris.append(patient_uri)

f = open("input_json/submitted_aligned_reads.json", "w")
f.write('[\n')
count=0
for patient_uri in patient_uris:
		json_obj = get_response_json_object(fhir_server + '/' + patient_uri)
		#print(json_obj)
		#break
		uuid = patient_uri.replace("Patient/", "")
		count = count + 1
		f.write('{\n')
		f.write('   "id" : "' + uuid + '",\n')
		f.write('   "name" : "submitted_aligned_reads",\n')
		f.write('   "submitter_id" : "' + uuid + '",\n')
		f.write('   "datetime" : "2020-11-04T14:32:19.373454+00:00",\n')
		f.write('   "error_type" : "file_size",\n')
		f.write('   "file_format" : "BAM",\n')
		f.write('   "file_name" : "foo.bam",\n')
		f.write('   "file_size" : 512,\n')
		f.write('   "file_state" : "registered",\n')
		f.write('   "md5sum" : "bdf121aadba028d57808101cb4455fa7",\n')
		f.write('   "object_id" : "dg.4503/' + uuid + '",\n')
		f.write('   "project_id" : "tutorial-synthetic_data_set_1",\n')
		f.write('   "state" : "uploading",\n')
		f.write('   "subject_id" : "p1011554-9",\n')
		f.write('   "participant_id": "' + uuid + '",\n')
		f.write('   "ga4gh_drs_uri" : "drs://example.org/dg.4503/' + uuid + '",\n')
		f.write('   "study_registration" : "example.com/study_registration",\n')
		f.write('   "study_id" : "aaa1234",\n')
		f.write('   "specimen_id" : "spec1111",\n')
#		f.write('   "updated_datetime" : "2020-11-04T14:32:19.373454+00:00",\n')
		if ('birthDate' in json_obj):
			f.write('   "birth_date" : "' + json_obj['birthDate'] + '",\n')
		if ('address' in json_obj):
			if ('state' in json_obj['address'][0]):
				f.write('   "state_abbrev" : "' + json_obj['address'][0]['state'] + '",\n')
			else:
				f.write('   "state_abbrev" : "' + 'MA' + '",\n')
			if ('postalCode' in json_obj['address'][0]):
				f.write('   "postal_code" : "' + json_obj['address'][0]['postalCode'] + '",\n')
			else:
				f.write('   "postal_code" : "' + '02130' + '",\n')
		f.write('   "experimental_strategy" : "Whole Genome Sequencing",\n')
		f.write('   "analysis_type" : "Aligned Sequence Read"\n')
		if (count == len(patient_uris)):
			f.write('}\n')
		else:
			f.write('},\n')

f.write(']\n')
f.close()

subprocess.check_call([
	'pfb', 'from', '-o', 'minimal_data.avro', 'json', '-s', 'minimal_schema.avro', '--program', 'DEV', '--project', 'test', 'input_json/'
])
