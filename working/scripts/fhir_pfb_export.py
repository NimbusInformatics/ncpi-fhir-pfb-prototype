# Given a FHIR server and auth token, this script runs a query, iterates through
# the matching patient results, and generates a PFB for the patients.

import requests
import sys
import json
import urllib3
import subprocess
from flatten_json import flatten

# Globals
patient_keys = dict()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fhir_server = sys.argv[1]
token = sys.argv[2]
condition = sys.argv[3]

headers = {"Authorization": "Bearer " + token}

def get_response_json_object(url):
	r = requests.get(url, headers=headers, verify=False)
	return r.json()

def main():
	resource_types=[]
	patient_uris = []
	count = 0;

	# Perform a search based on conditions
	# TODO: we need to make this more generic, remove hard-coded limit
	json_obj = get_response_json_object(fhir_server + '/Condition?_count=25&code:text=' + condition)

	# Collect all the patient records
	# eliminate duplicates
	previous_patients = dict()
	if ('entry' in json_obj):
		for entry in json_obj['entry']:
			patient_uri = entry['resource']['subject']['reference']
			if patient_uri in previous_patients.keys():
				continue
			else:
				previous_patients[patient_uri] = 1
				print('Found matching patient:', patient_uri)
				patient_uris.append(patient_uri)

	f = open("input_json/patient.json", "w")
	f.write('[\n')
	count=0
	for patient_uri in patient_uris:
		if (count > 0):
			f.write(',\n')
		json_obj = get_response_json_object(fhir_server + '/' + patient_uri)
		# for more information on the flatten method see https://towardsdatascience.com/flattening-json-objects-in-python-f5343c794b10
		flat_json = flatten(json_obj, '_')
		# Adding the keys from the JSON seen for each patient so we can later add
		# them to the PFB schema.
		track_patient_keys(flat_json)
		convert_values_to_strings(flat_json)
		print(json.dumps(flat_json))
		uuid = patient_uri.replace("Patient/", "")
		# making sure we have at least these defined
		flat_json['submitter_id'] = uuid
		flat_json['id'] = uuid
		f.write(json.dumps(flat_json))
		f.write('\n')
		count = count + 1
	f.write(']\n')
	f.close()

	#print(json.dumps(patient_keys))

	# update the PFB schema based on fields seen in all patients
	json_schema = json.load(open('minimal_file.json', 'r'))
	extend_patient_schema(json_schema)
	print(json.dumps(json_schema['_definitions.yaml']['workflow_properties']))
	write_json_schema_to_pfb(json_schema, 'minimal_schema.avro')

	# write out the FHIR patient data as PFB
	write_fhir_patients_to_pfb()



# adds patient flatten keys to shared object
def track_patient_keys(json_obj):
	for curr_key in json_obj:
		if curr_key in patient_keys.keys():
			continue
		else:
			patient_keys[curr_key] = 1

def extend_patient_schema(json_schema):
	for curr_key in patient_keys.keys():
		json_schema['_definitions.yaml']['patient_properties'][curr_key] = { 'type': 'string'}
	print(json.dumps(json_schema['_definitions.yaml']['patient_properties']))

def write_json_schema_to_pfb(json_schema, output_avro_file):
	f = open("extended_minimal_file.json", 'w')
	f.write(json.dumps(json_schema))
	f.close()
	subprocess.check_call([
		'pfb', 'from', '-o', 'minimal_schema.avro', 'dict', 'extended_minimal_file.json'
	])

def write_fhir_patients_to_pfb():
	subprocess.check_call([
		'pfb', 'from', '-o', 'minimal_data.avro', 'json', '-s', 'minimal_schema.avro', '--program', 'DEV', '--project', 'test', 'input_json/'
	])

def convert_values_to_strings(json_struct):
	for curr_key in json_struct.keys():
		json_struct[curr_key] = str(json_struct[curr_key])

if __name__ == '__main__':
    main()
