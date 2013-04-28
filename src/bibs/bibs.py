import os, sys
import glob
import urllib2, urllib
import yaml, json
from dict2xml import dict2xml
import xmltodict
from lxml import etree
import re
import copy
import pprint
from collections import OrderedDict
from StringIO import StringIO

class Bibs(object):

    source_dir = 'sources/'

    def __init__(self):
        self.sources = {}
        self.find_sources()


    def find_sources(self):
        self.sourcefile_list = glob.glob(os.path.dirname(__file__) + 
                                     '/' + Bibs.source_dir + '*.yaml')
        self.source_list = []
        for sourcefile in self.sourcefile_list:
            self.source_list.append(os.path.basename(sourcefile).split('.yaml')[0])


    def load_source(self, namespace):
        for source_file in self.sourcefile_list:
            match = re.match('^(?i)'+namespace+'.yaml$', os.path.basename(source_file))
            if match:
                f = open(source_file, 'r')
                y = yaml.load(f)
                self.sources[y['namespace']] = y
                return copy.deepcopy(y)
        raise Exception('Invalid Source.')


    def get_source(self, source):
        if source in self.sources:
            return copy.deepcopy(self.sources[source])
        elif source is not None and source not in self.sources:
            return self.load_source(source)
        else:
            raise Exception('Invalid source \'' + str(source) + '\'')


    def search(self, input_string, source=None, api='default', 
               return_format='', pretty_print=False):
        search_source = self.get_source(source)

        query_object = self.create_query_object(input_string, search_source, api)
        query_object.parse_input_elements()
        query_object.parse_input_options()
        query_object.determine_format()
        query_object.enforce_requirements()
        query_object.build_string()
        #return
        request = urllib2.urlopen(query_object.query_string)
        results = request.read()
        results = self.convert_results(results, query_object.output_format, 
                                       return_format)
        if pretty_print:
            pprint.pprint(results)
        return results        


    def convert_results(self, results, output_format, return_format):
        if output_format == 'json':
            if return_format.lower() == 'xml':
                results = dict2xml(json.loads(results))
            elif return_format.lower() == 'object':
                results = self.json_to_object(json.loads(results), 'QueryObject')
            else:
                results = json.loads(results)
        elif output_format == 'xml':
            if return_format.lower() == 'json':
                results = json.loads(json.dumps(xmltodict.parse(results)))
            elif return_format.lower() == 'object':
                jsonresults = json.loads(json.dumps(xmltodict.parse(results)))
                results = self.json_to_object(jsonresults, 'QueryObject')
        elif output_format == 'javascript':
            if return_format.lower() in ('json', 'xml', 'object'):
                print ('Cannot Convert \'JavaScript\' response to \'' + 
                       return_format.lower() +'\'...returning \'JavaScript\'')
            pass
        return results


    def json_to_object(self, json, classname):
        cls = 'QueryObjectSubElement'
        if isinstance(json, list):
            object_list = []
            for item in json:
                object_list.append(self.json_to_object(item, classname))
            return object_list
        elif isinstance(json, dict):
            object_dict = {}
            for key, value in json.items():
                key = self.make_valid_python_variable_name(key)
                if isinstance(value, list):
                    object_list = []
                    for item in value:
                        object_list.append(self.json_to_object(item, cls))
                    object_dict[key] = object_list
                elif isinstance(value, dict):
                    object_dict[key] = self.json_to_object(value, cls)
                else:
                    object_dict[key] = value
            return type(classname, (), object_dict)


    def make_valid_python_variable_name(self, string):
        return re.sub('[^a-zA-Z0-9_]', '__', string)
        

    def help(self, source=None, api=None, detail=None):
        if source is None:
            print '-----------\nSource List\n-----------\n'
            pprint.pprint(self.source_list)
            return
        search_source = self.get_source(source)
        if api is not None and api in search_source['api']:
            if detail is not None:
                query = detail.split('->')
                path, entry = self.find_param(query, search_source['api'][api])
                if entry is not None:
                    ws = '   '
                    buf = StringIO()
                    print 'Path to \''+detail+'\':'   
                    for num, p in enumerate(path):
                        if num == len(path)-1:
                            pprint.pprint(entry, stream=buf)
                            print ws + p + '-> (... \n\n' + buf.getvalue() + ws +'...)'
                        else:
                            print ws + p
                        ws += '   '                    

            elif 'help' in search_source['api'][api]:
                print search_source['api'][api]['help']
                if 'required' in search_source['api'][api]['input']:
                    required = search_source['api'][api]['input']['required']
                else:
                    required = None
                params = search_source['api'][api]['input']['params']
                options = search_source['api'][api]['input']['options']
                for input_type, input_data in OrderedDict([('Required:', required),
                                                           ('Parameters:', params),
                                                           ('Options:', options)]).items():
                    if input_data is not None:
                        print input_type
                        string = ''
                        width = 0
                        if 'keywords' in input_data:
                            for k in input_data['keywords']:
                                if len(k) > width: width = len(k)
                            for k in input_data['keywords']:
                                print '\t{:>{}}'.format(k, width)
                        else:
                            for name, entry in input_data.items():
                                if len(name) > width: width = len(name)
                            for name, entry in input_data.items():
                                string += '\t{:>{}}'.format(name, width)
                                if 'mode' in entry:
                                    string += '  <mode:' + entry['mode'] + '>\n'
                                else:
                                    string += '\n'
                        print string

        elif 'help' in search_source:
            print search_source['help']


    def determine_format(self):
        if 'option' in self.query_elements:
            for arg in self.query_elements['option']:
                prefix = arg['prefix']
                value = arg['value']
                if prefix == 'format':
                    self.output_format = value
                    return
                

    def enforce_requirements(self):        
        self.check_required()
        self.check_minimum()
        

    def check_minimum(self):        
        if 'prototype' in self.query_elements:
            prototype_params = self.prototype['parameters']
            if prototype_params is None:
                return
            for param in prototype_params:
                for arg in self.query_elements['field']:
                    for i in ('prefix', 'entry'):
                        try:
                            if param in arg[i]:
                                return
                        except:
                            continue
            if self.proto_optional:
                if len(self.proto_optional) == len(prototype_params):
                    return
            proto = self.query_elements['prototype']['value']
            raise Exception('Prototype \'' + proto + 
                            '\' requires atleast one argument.')
        else:
            if len(self.query_elements['field']) < 1:
                raise Exception(self.__class__.__name__ + '\'s api \''+
                                self.api+'\' requires atleast one argument.')


    def check_required(self):
        for mode, items in OrderedDict([('global', self.global_required),
                                        ('required', self.proto_required),
                                        ('conditional', self.proto_cond_req)]).items():
            if items is None:
                continue

            required = items['keywords']
            
            if isinstance(required, dict):
                new_list = []
                for key in required.keys():
                    new_list.append(key)
                required = new_list

            found = []
            for n, r in enumerate(required):
                for element in self.query_elements['field']:
                    for i in ('prefix', 'entry'):
                        try:
                            if r in element[i]:
                                found.append(r)
                                break 
                        except:
                            continue

            if mode in ('global', 'required'):
                if len(required) != len(found):
                    raise Exception('Missing required argument(s)...Found:\''+
                                    str(found)+'\'  Required:\''+str(required)+'\'')
            elif mode == 'conditional':
                if len(found) > 0 and len(required) != len(found):
                    raise Exception('Missing conditional argument(s)...Found:\''+
                                    str(found)+'\'  Required:\''+str(required)+'\'')

    
    def build_arg_string(self, mode):        
        if mode not in self.query_elements:
            return
        
        for num, arg in enumerate(self.query_elements[mode]):
            entry = arg['entry']
            prefix = arg['prefix']
            value = arg['value']
            syntax = arg['syntax']
            
            if isinstance(prefix, dict):
                entry = prefix
                self.query_elements[mode][num]['prefix'] = None

            arg['string'] = ''

            if isinstance(value, dict): 
                if value['value']:
                    if 'args' in syntax:
                        char = syntax['args']
                    else:
                        char = syntax['bind']
                    value = value['prefix'] + char + value['value']
                else:
                    value = value['prefix']
            
            if isinstance(entry, dict):
                entry = self.assign_dict_value(entry, value)
                if self.input_type == 'json':
                    arg['string'] += ',' + re.sub('(^\{|\}$| )', '', str(entry).replace("'", "\""))
                else:
                    for k,v in entry.items():
                        arg['string'] += k + syntax['bind'] + str(v).replace(' ','')
            else:
                if self.input_type == 'json':
                    if value == 'null':
                        arg['string'] += ",\""+entry+"\":"+value+""
                    else:
                        arg['string'] += ",\""+entry+"\":\""+value+"\""
                else:
                    if prefix and entry and value:
                        arg['string'] += entry + syntax['args'] + urllib.quote(value)
                    elif prefix and entry:
                        arg['string'] += entry
                    elif entry and value:
                        arg['string'] += entry + syntax['bind'] + urllib.quote(value)
                        
            #print 'string:', arg['string']


    def build_string(self):
        for mode in ('prototype', 'field', 'option'):
            self.build_arg_string(mode)
       
        string = []
        for mode in ('prototype','field', 'option'):
            if mode in self.query_elements:
                for num, arg in enumerate(self.query_elements[mode]):                    
                    syntax = arg['syntax']
                    if self.input_type == 'json':
                        string.append(arg['string'])
                    else:
                        if arg['prefix']:
                            if (syntax['chain'] + arg['prefix']) not in string:
                                string.append(syntax['chain'] + arg['prefix'])
                                string.append(syntax['bind'] + arg['string'])
                            else:
                                string.append(arg['string'])
                            prefix = arg['prefix']
                            self.query_elements[mode][num] = None
                            if 'multi' in syntax:
                                for num, arg in enumerate(self.query_elements[mode]):                    
                                    if arg and prefix == arg['prefix']:
                                        string.append(syntax['multi'])
                                        break                
                        else:
                            string.append(syntax['chain'] + arg['string'])

        string = ''.join(string)
        if self.input_type == 'json':
            string = string.lstrip(',')
            self.query_string = self.url + self.path.format('{' + string + '}')
        else:
            for mode in ('prototype','field', 'option'):
                if mode in self.syntax:
                    for char in ('bind', 'chain', 'multi'):
                        if char in self.syntax[mode]:
                            string = string.lstrip(self.syntax[mode][char])
                            string = string.rstrip(self.syntax[mode][char])
                    
            self.query_string = self.url + self.path.format(string)

        print '\n' + self.query_string + '\n'
        

    def assign_list_value(self, param_list, value):
        if len(param_list) == 1:
            prefix = param_list.pop()
        else: 
            prefix = None
        values = value.split('|')
        for v in values:
            v = urllib2.quote(v.lstrip(' ').rstrip(' '))
            if prefix:
                v = prefix + v
            param_list.append(v)
        return param_list


    def assign_dict_value(self, param_dict, value):
        for param, entry in param_dict.items():            
            if isinstance(entry, str):
                if self.multi_value:
                    value = re.sub('(?<!\\\\)\|', self.syntax['multi']['bind'], value)
                param_dict[param] += urllib2.quote(str(value))
                param_dict[param] = param_dict[param].lstrip(' ').rstrip(' ')
                return param_dict
            elif isinstance(entry, list):
                param_dict[param] = self.assign_list_value(entry, value)
                return param_dict
            else:
                param_dict[param] = self.assign_dict_value(entry, value)
                return param_dict


    def parse_input_options(self):
        self.query_elements['option'] = []
        for elements in self.input_options:
            arg = elements[:-1]
            value = [elements[-1],][0]
            path, entry = self.find_param(arg, self.options)            
            if not entry:
                    raise Exception('Invalid parameter \''+str(arg)+'\'')                

            syntax = self.get_syntax(self.options, path, 'option')            
            prefix = self.get_prefix(self.options, path)
                        
            self.query_elements['option'].append({'entry': entry, 
                                                  'prefix': prefix, 
                                                  'value': value,
                                                  'syntax': syntax})

    def parse_input_elements(self):
        self.query_elements['field'] = []
        for elements in self.input_elements:
            
            arg = elements[:-1]
            value = [elements[-1],][0]
            
            if self.params is None:
                self.add_field_arg('', value) 
                continue
            
            if self.global_required:
                if self.parse_with_global_required(arg, value):
                    continue

            if self.prototype:
                self.parse_with_prototype(arg, value)
            else:
                path, entry = self.find_param(arg, self.params)                            
                if not entry:
                    raise Exception('Invalid parameter \''+str(arg)+'\'')                
                
                root = path[0]                

                if 'mode' in self.params[root]:
                    mode = self.params[root]['mode']
                else:
                    mode = self.params['mode']
                
                syntax = self.get_syntax(self.params, path, mode)
                prefix = self.get_prefix(self.params, path)

                if mode == 'field':
                    self.add_argument(entry, prefix, value, syntax)

                elif mode == 'prototype':                    
                    self.parse_prototype(entry, prefix, value, syntax)

        #print '\n' + str(self.query_elements)


    def get_syntax(self, parameter, path, mode):
        syntax = None
        _path = copy.copy(path)
        if path:
            for p in _path:
                if p in parameter:
                    if 'syntax' in parameter[p]:
                        return parameter[p]['syntax']
                    else:
                        _path.pop(0)
                        syntax = self.get_syntax(parameter[p], _path, mode)
        if syntax is None:
            if self.syntax:
                if mode in self.syntax:
                    syntax = self.syntax[mode]
        return syntax


    def get_prefix(self, parameter, path):
        prefix = None
        _path = copy.copy(path)
        if path:
            for p in _path:
                if p in parameter:
                    if 'prefix' in parameter[p]:
                        return parameter[p]['prefix']
                    else:
                        _path.pop(0)
                        return self.get_prefix(parameter[p], _path)
        return prefix


    def add_argument(self, entry, prefix, value, syntax):
        if isinstance(entry, list):
            entry = entry[-1]
        self.query_elements['field'].append({'prefix': prefix, 
                                             'entry':entry, 
                                             'value':value,
                                             'syntax': syntax})


    def parse_with_global_required(self, arg, value):
        path, entry = self.find_param(arg, self.global_required)
        mode = self.global_required['mode']
        syntax = self.get_syntax(self.global_required, path, mode)
        prefix = self.get_prefix(self.global_required, path)
        if entry:
            self.query_elements['field'].append({'prefix': prefix, 
                                                 'entry': entry,
                                                 'value': value,
                                                 'syntax': syntax})
            return True
        else:
            return False


    def parse_with_prototype(self, arg, value):
        if 'parameters' not in self.prototype:
            raise Exception('Invalid prototype \''+self.prototype+'\'')
        path, entry = self.find_param(arg, self.prototype['parameters'])
        if entry is None:
            raise Exception('Invalid parameter \''+str(arg)+'\'')
        root = path[0]
        d = {}
        def get_nested(d, l, e):
            if len(l) != 0:
                item = l.pop(0)
                d[item] = {}
                result = get_nested(d[item], l, e)
                if result is not None:
                    d[item] = result
                else:
                    d[item] = e
                return d
        
        entry = get_nested(d, path, entry)    
        syntax = self.get_syntax(self.prototype['parameters'], path, 'prototype')
        prefix = self.get_prefix(entry, path)

        self.query_elements['field'].append({'prefix': prefix, 
                                             'entry': entry, 
                                             'value': value,
                                             'syntax': syntax})


    def parse_prototype(self, entry, prefix, value, syntax):
        if 'prototype' not in self.query_elements:
            self.query_elements['prototype'] = []
        path, proto_entry = self.find_param((value,), entry)
        if not proto_entry:
            raise Exception('Invalid prototype \''+str(value)+'\'')
        proto_param = path[0]
        self.prototype = proto_entry
        
        if 'required' in self.prototype:
            self.proto_required = self.prototype['required']
        if 'cond_req' in self.prototype:
            self.proto_cond_req = self.prototype['cond_req']
        if 'optional' in self.prototype:
            self.proto_optional = self.prototype['optional']

        #syntax = self.get_syntax(entry, path, 'prototype')
        #key = self.get_key(entry, path)

        self.query_elements['prototype'].append({'prefix': prefix, 
                                                 'entry': proto_param, 
                                                 'value': value,
                                                 'syntax': syntax})
                
    
    def find_param(self, args, params):   
        if isinstance(args, str):
            args = [args,]
        path = []
        entry = None

        def flatten_path(_p, _path):
            for i in _p:
                if isinstance(i, list):
                    _path = flatten_path(i, _path)
                else:
                    if i not in _path:
                        _path.append(i)
            return _path

        for arg in args:
            arg = re.escape(arg)
            entry = self.search_entries(arg, params)                        
            if entry:
                params = entry
                if isinstance(entry, list):
                    p = entry.pop(0)
                    if isinstance(p, str):
                        p = [p]
                    path = flatten_path(p, path)
                    entry = entry[0]                                        
        if entry is not None:
            return [path, entry]
        return [None, None]


    def search_entries(self, arg, params):
        if params == []:
            params = list
        match = None
        if isinstance(params, dict):
            match = self.find_dict_entry(arg, params)
        elif isinstance(params, (list, tuple)):
            match = self.find_list_entry(arg, params)                    
        return match


    def find_dict_entry(self, arg, params):
        for param, entry in params.items():
            match = re.match('^(?i)'+arg+'$', param)
            if match:
                path = param
                return [path, entry]          
        if not match:
            for param, entry in params.items():
                match = self.search_entries(arg, entry)
                if match:
                    if isinstance(match, list):
                        path = [param, match.pop(0)]
                        match = match[-1]
                    elif isinstance(match, str):
                        path = param
                    return [path, match]
        return None


    def find_list_entry(self, arg, params):
        for param in params:
            if isinstance(param, dict):
                match = self.find_dict_entry(arg, param)        
                if match:
                    path, entry = match
                    return [path, entry]
            elif isinstance(param, (list, tuple)):
                match = self.find_list_entry(arg, param)
                if entry:
                    path, entry = match
                    return [path, param]
            else:
                match = re.match('^(?i)'+arg+'$', param)
                if match:
                    return param
    

    def create_query_object(self, input_string, source, api):
        query_class = type(source['namespace'], (Bibs,), {})
        query_object = query_class()
        query_object.url = source['url']
        query_object.api = api
        query_object.path = source['api'][api]['path']
        query_object.input_type = source['api'][api]['input']['type']
        query_object.output_format = source['api'][api]['output']['default']
        query_object.prototype = None
        query_object.proto_required = None
        query_object.proto_cond_req = None
        query_object.proto_optional = None
        query_object.input_string = input_string
        query_object.input_elements = []
        query_object.input_options = []
        query_object.query_string = ''
        query_object.query_elements = {}
        query_object.params = source['api'][api]['input']['params']
        query_object.options = source['api'][api]['input']['options']
        
        if 'required' in source['api'][api]['input']:
            query_object.global_required = source['api'][api]['input']['required']
        else:
            query_object.global_required = None

        if 'multi_value' in source['api'][api]['input']:
            query_object.multi_value = True
        else:
            query_object.multi_value = False
            
        if 'syntax' in source['api'][api]['input']:
            query_object.syntax = {}
            source_syntax = source['api'][api]['input']['syntax']
            for mode in ('prototype', 'field', 'option', 'multi', 'args'):
                if mode in source_syntax:
                    query_object.syntax[mode] = source_syntax[mode]
                else:
                    query_object.syntax[mode] = {'bind': None, 'chain': None}
        else:
            query_object.syntax = None

        query_object.format_input_string()        
        return query_object


    def format_input_string(self):
        input_elements = input_options = None
        elements = re.split('(?<!\\\\)@', self.input_string)                
        if len(elements) == 2:
            input_elements, input_options = elements
        elif len(elements) == 1:
            input_elements = elements[0]
        else:
            raise Exception('Invalid use of \'@\'')
        self.input_elements = self.lex(input_elements)
        if input_options:
            self.input_options = self.lex(input_options)


    def lex(self, string):
        elements = self.split_and_strip(string)
        return elements


    def split_and_strip(self, string):
        elements = re.split('(?<!\\\\):', string)
        new_elements = []
        for num, element in enumerate(elements):
            element = re.sub('\\\\:', ':', element)
            element = re.sub('\\\\@', '@', element)
            new_elements.append(element.lstrip(' ').rstrip(' ').split('->'))
        return new_elements


    
