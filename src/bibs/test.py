# to run the tests, change into the directory that contains this file
# and do 'python test.py. testing involves getting commands and expected
# output from tests/source_test.yaml files, calling get_url() from bibs.py
# and comparing the returned url to the expected output.   
#
# TODO: Add *a lot* more tests
#
# NOTE: You'll probably want to reduce the font size of your terminal to 
# display the table in full.

import os
from glob import glob
import yaml
from bibs import Bibs

b = Bibs()

sourcetest_files = glob('tests/*.yaml')
testcases = {}

for f in sourcetest_files:
    fname = os.path.basename(f).split('_test.yaml')[0]
    with open(f, 'r') as f:
        testcases[fname] = yaml.load(f)

def run_test(case, command, source, api, expected_url):
    try:
        output = b.get_url(command, source, api)
    except Exception as e:
        print('EXCEPTION:  ', source, api, case, command, str(e))
        return
    if expected_url == output:
        print('{:<20} {:<20} {:<20} ({:<15}) {:>{}}'.format(source, api, case, command, 
                                                     '[PASS]', abs(120-len(command))))
    else:
        print('\n{:<20} {:<20} {:<20} ({:<15}) {:>{}} \n\n\tEXPECTED=>{}\n\t  OUTPUT=>{}\n'
              .format(source, api, case, command, '[FAIL]', 
                      abs(120-len(command)), expected_url, output))

def test_cases(source, apis):   
    for api, parameters in apis.items():
        for parameter, args in parameters.items():
            for arg, entries in args.items():
                if 'CASES' in entries:
                    for command, expected_url in entries['CASES'].items():
                        run_test(arg, command, source, api, expected_url)
                else:
                    path, entry = b.find_param('CASES', args)
                    for command, expected_url in entry.items():
                        run_test(arg, command, source, api, expected_url)
                                        
for source, apis in testcases.items():
    test_cases(source, apis)
        
