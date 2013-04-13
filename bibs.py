import os, sys
import glob
import urllib2, urllib
import yaml, json
import re
import copy
import pprint
from collections import OrderedDict

class Bibs(object):

    source_dir = 'sources/'

    def __init__(self):
        self.sources = {}
        self.find_sources()


    def find_sources(self):
        self.source_list = glob.glob(sys.path[1] + '/' + Bibs.source_dir + '*.yaml')
        

    def load_source(self, namespace):
        for source_file in self.source_list:
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


    def search(self, input_string, source=None, api='default'):
        search_source = self.get_source(source)

        query_object = self.create_query_object(input_string, search_source, api)
        query_object.parse_input_elements()
        query_object.parse_input_options()
        query_object.enforce_requirements()
        query_object.build_string()
        #return
        request = urllib2.urlopen(query_object.query_string)
        results = request.read()
        #pprint.pprint(json.loads(results))
        return results        


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
                    if param in arg['key']:
                        return
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

            required = items['keys']
            
            if isinstance(required, dict):
                new_list = []
                for key in required.keys():
                    new_list.append(key)
                required = new_list

            found = []
            for n, r in enumerate(required):
                for element in self.query_elements['field']:
                    if r in element['key']:
                        found.append(r)
                        break 

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
        
        for arg in self.query_elements[mode]:
            arg['string'] = ''
            key = arg['key']
            value = arg['value']
            
            if isinstance(value, dict): 
                if value['value']:
                    if 'args' in self.syntax[mode]:
                        char = self.syntax[mode]['args']
                    else:
                        char = self.syntax[mode]['bind']
                    value = value['key'] + char + value['value']
                else:
                    value = value['key']
            
            if isinstance(key, dict):
                key = self.assign_dict_value(key, value)
                if self.parse_type == 'json':
                    arg['string'] += ',' + re.sub('(^\{|\}$| )', '', str(key).replace("'", "\""))
                else:
                    for k,v in key.items():
                        arg['string'] += k + self.syntax[mode]['bind'] + str(v).replace(' ','')
            else:
                if self.parse_type == 'json':
                    if value == 'null':
                        arg['string'] += ",\""+key+"\":"+value+""
                    else:
                        arg['string'] += ",\""+key+"\":\""+value+"\""
                else:
                    if mode=='filter':
                        arg['string'] += value #+ self.syntax[mode]['chain']
                    else:
                        arg['string'] += key + self.syntax[mode]['bind'] + value
                    
            #print 'key:', str(key), 'value:', str(value)
            #print 'string:', arg['string']



    def build_string(self):
        for mode in ('prototype', 'field', 'option', 'filter'):
            self.build_arg_string(mode)
       
        string = ''
        for mode in ('prototype','field', 'filter', 'option'):
            if mode in self.query_elements:

                if self.syntax and mode in self.syntax:
                    bind = self.syntax[mode]['bind'] if self.syntax[mode]['bind'] else ''
                    chain = self.syntax[mode]['chain'] if self.syntax[mode]['chain'] else ''
                    if 'multi' in self.syntax[mode]:
                        multi = self.syntax[mode]['multi'] if self.syntax[mode]['multi'] else ''
                    else:
                        multi = ''
                else:
                    bind = chain = multi = ''

                for num, arg in enumerate(self.query_elements[mode]):                    
                    if self.parse_type == 'json':
                        string += arg['string']
                    else:
                        if mode == 'filter':
                            if num == 0:
                                string += arg['key'] + bind + arg['string'] + multi
                            elif num < len(self.query_elements[mode])-1:
                                string += arg['string'] + multi
                            else:
                                string += arg['string'] + chain
                        else:
                            string += arg['string']
                            if num < len(self.query_elements[mode]):
                                string += chain
                        
        if self.parse_type == 'json':
            string = string.lstrip(',')
            self.query_string = self.url + self.path.format('{' + string + '}')
        else:
            for mode in ('prototype','field', 'filter', 'option'):
                if mode in self.syntax:
                    string = string.rstrip(self.syntax[mode]['bind'])
                    string = string.rstrip(self.syntax[mode]['chain'])
            self.query_string = self.url + self.path.format(string)

        #print '\n' + self.query_string + '\n'
        

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


    def parse_with_prototype(self, arg, value):
        if 'parameters' not in self.prototype:
            raise Exception('Invalid prototype \''+self.prototype+'\'')
        path, entry = self.find_param(arg, self.prototype['parameters'])
        if entry is None:
            raise Exception('Invalid parameter \''+str(arg)+'\'')
        root = path[0]

        key = {}
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
        key = get_nested(key, path, entry)

        self.query_elements['field'].append({'key': key, 
                                             'value': value})


    def parse_input_options(self):
        self.query_elements['option'] = []
        for elements in self.input_options:
            arg = elements[:-1]
            value = [elements[-1],][0]
            path, entry = self.find_param(arg, self.options)            
            if not entry:
                    raise Exception('Invalid parameter \''+str(arg)+'\'')                
            self.query_elements['option'].append({'key': entry, 'value': value})


    def parse_input_elements(self):
        self.query_elements['field'] = []
        self.query_elements['filter'] = []
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
                
                if mode == 'field':
                    self.add_field_arg(entry, value)                
                if mode == 'filter':
                    self.add_filter_arg(path, entry, value)
                elif mode == 'prototype':                    
                    self.parse_prototype(entry, value)

        #print '\n' + str(self.query_elements)


    def parse_with_global_required(self, arg, value):
        path, entry = self.find_param(arg, self.global_required)
        if entry:
            self.query_elements['field'].append({'key': entry,
                                                 'value': value})
            return True
        else:
            return False


    def add_filter_arg(self, path, entry, value):
        entry_dict = None
        if isinstance(entry, (dict, list)):
            path, entry = self.find_param((value,), entry)
            entry_dict = {'key': path[0], 'value': entry}
        else:
            entry_dict = {'key': path[0], 'value':
                              {'key':entry, 'value': value}}
        if entry_dict is not None:
            self.query_elements['filter'].append(entry_dict)


    def add_field_arg(self, entry, value):
        if isinstance(entry, list):
            entry = entry[-1]
        self.query_elements['field'].append({'key':entry, 'value':value})


    def parse_prototype(self, entry, value):
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
            
        if 'key' in entry:
            key = entry['key']
        else:
            key = proto_entry['key']
                
        self.query_elements['prototype'].append({'key': key, 
                                                 'value': proto_param})
        
    
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
        query_object.parse_type = source['api'][api]['input']['type']
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
            for mode in ('prototype', 'field', 'option', 'filter', 'multi'):
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


    
