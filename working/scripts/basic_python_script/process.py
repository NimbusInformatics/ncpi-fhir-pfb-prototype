#!/usr/bin/env python3

import argparse
import subprocess
import requests
import json
import sys
import os
import requests


def main():
    print ("test")
    parser = argparse.ArgumentParser(description='Process JSON file.')
    parser.add_argument('--json')
    args = parser.parse_args()
    if len(sys.argv) == 0:
        parser.print_help()
    if args.json:
        with open(args.json, 'r') as f:
            d = json.load(f)
        # print (json.dumps(d))
        for key in d:
            print (key + "\t" + d[key])

if __name__ == '__main__':
    main()

