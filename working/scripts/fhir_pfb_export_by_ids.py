# Given a FHIR server and auth token, this script runs a query, iterates through
# the matching patient results, and generates a PFB for the patients.

import argparse
import datetime
import requests
import sys
import json
import urllib3
import subprocess
from flatten_json import flatten

# python3 fhir_pfb_export_by_ids.py --file sample_fhir_ids_input.json --token $(gcloud auth application-default print-access-token) --gcs_bucket nimbus-pfb-test

# Globals
patient_keys = dict()
docref_keys = dict()
timestr = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_response_json_object(url, headers, cookies):
	r = requests.get(url, headers=headers, cookies=cookies, verify=False, allow_redirects=True)
#	print('status:', r.status_code, 'content-type', r.headers['content-type'], 'url', r.url, 'text', r.text)
	return r.json()

def main():
	args = parse_args()
	
	json_obj = json.load(args.file)
	fhir_server = json_obj['fhir_server_base_uri']
	token = args.token
	cloud_bucket = args.gcs_bucket
	cookies = {}
	if (args.cookies != ''):
		cookies = json.loads(args.cookies)

	headers = {}
	if (token is not None and token != ''):
		headers = {"Authorization": "Bearer " + token}
	resource_types=[]
	patient_uris = []
	count = 0;

	for patient_uri in json_obj['ids']:
		print('Found matching patient:', patient_uri)
		patient_uris.append(patient_uri)

	# patients
	f = open("input_json/patient.json", "w")
	f.write('[\n')
	count=0
	for patient_uri in patient_uris:
		if (count > 0):
			f.write(',\n')
		json_obj = get_response_json_object(fhir_server + '/' + patient_uri, headers, cookies)

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

	# patient ref docs
	# TODO: we should iterate over each doc reference individually rather than collapse the whole structure
	# that will prevent the names from having entry_0... in them...
	f = open("input_json/document_reference.json", "w")
	f.write('[\n')
	count=0
	for patient_uri in patient_uris:
		print ("PATIENT URI: "+patient_uri)
		if (count > 0):
			f.write(',\n')
		#/Patient/7da367de-ad47-47ad-a0f8-ed3688058d4c
		json_obj = get_response_json_object(fhir_server + '/DocumentReference/?subject=' + patient_uri, headers, cookies)
		flat_json = flatten(json_obj, '_')
		convert_values_to_strings(flat_json)
		print(json.dumps(json_obj))
#		print('flat_json:', flat_json)
		if (flat_json['total'] != "0"):
			uuid = flat_json['entry_0_resource_id']
			patient_uuid = patient_uri.replace("Patient/", "")
			# making sure we have at least these defined
			flat_json['submitter_id'] = uuid
			flat_json['file_name'] = flat_json['entry_0_resource_identifier_0_value']
			flat_json['object_id'] = uuid
			flat_json['patient_id'] = patient_uuid
			flat_json['ga4gh_drs_uri'] = flat_json['entry_0_resource_content_0_attachment_url']
			track_docref_keys(flat_json)
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
	extend_docref_schema(json_schema)
	write_json_schema_to_pfb(json_schema, 'minimal_schema.' + timestr + '.avro')

	# write out the FHIR patient data as PFB
	write_fhir_patients_to_pfb()
	upload_pfb_to_google_cloud(cloud_bucket)



# adds patient flatten keys to shared object
def track_patient_keys(json_obj):
	for curr_key in json_obj:
		if curr_key in patient_keys.keys():
			continue
		else:
			patient_keys[curr_key] = 1

# adds patient flatten keys to shared object
def track_docref_keys(json_obj):
	for curr_key in json_obj:
		if curr_key in docref_keys.keys():
			continue
		else:
			docref_keys[curr_key] = 1

def extend_docref_schema(json_schema):
	for curr_key in docref_keys.keys():
		json_schema['_definitions.yaml']['document_reference_properties'][curr_key] = { 'type': 'string'}
	print(json.dumps(json_schema['_definitions.yaml']['document_reference_properties']))

def extend_patient_schema(json_schema):
	for curr_key in patient_keys.keys():
		json_schema['_definitions.yaml']['patient_properties'][curr_key] = { 'type': 'string'}
	print(json.dumps(json_schema['_definitions.yaml']['patient_properties']))

def write_json_schema_to_pfb(json_schema, output_avro_file):
	f = open("extended_minimal_file.json", 'w')
	f.write(json.dumps(json_schema))
	f.close()
	subprocess.check_call([
		'pfb', 'from', '-o', output_avro_file, 'dict', 'extended_minimal_file.json'
	])

def write_fhir_patients_to_pfb():
	subprocess.check_call([
		'pfb', 'from', '-o', 'minimal_data.' + timestr + '.avro', 'json', '-s', 'minimal_schema.' + timestr + '.avro', '--program', 'DEV', '--project', 'test', 'input_json/'
	])


def upload_pfb_to_google_cloud(cloud_bucket):
	subprocess.check_call([
		'gsutil', 'cp','minimal_data.' + timestr + '.avro', 'gs://' + cloud_bucket
	])
	print ("Cloud Copy complete.")
	print ("To import into Terra, use https://app.terra.bio/#import-data?format=PFB&url=https://storage.googleapis.com/" + cloud_bucket + '/minimal_data.' + timestr + '.avro')

def convert_values_to_strings(json_struct):
	for curr_key in json_struct.keys():
		json_struct[curr_key] = str(json_struct[curr_key])

def parse_args():
	parser = argparse.ArgumentParser(description='Export PFB from FHIR.')
	parser.add_argument('--file', type=argparse.FileType('r'), required=True, help='JSON file of FHIR IDs')
	parser.add_argument('--token', type=str, help='token')
	parser.add_argument('--cookies', type=str, help='cookies, in JSON format')	
	parser.add_argument('--gcs_bucket', type=str, required=True, help='gcs_bucket')
	
	args = parser.parse_args()
	if (len(sys.argv) == 0):
		parser.print_help()
	return args	

if __name__ == '__main__':
    main()
