import os, sys
import glob
import urllib2, urllib
import yaml, json
import re
import copy
import pprint

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
        query_object.build_string()
        #return
        request = urllib2.urlopen(query_object.query_string)
        results = request.read()
        #pprint.pprint(json.loads(results))
        return results        
        

    def build_prototype_string(self):        
        if 'prototype' in self.query_elements:
            self.query_elements['prototype']['string'] = ''
            value = self.query_elements['prototype']['value']
            key = self.query_elements['prototype']['key']
            for k,v in key.items():
                key[k] += value
            if self.parse_type == 'json':
                self.query_elements['prototype']['string'] += re.sub('(^\{|\}$| )', '', 
                                                                     str(key).replace("'", "\""))
            else:
                for k,v in key.items():
                    self.query_elements['prototype']['string'] += k + self.param_bind_char + v

    
    def build_arg_string(self, e):        
        for arg in self.query_elements[e]:
            arg['string'] = ''
            key = arg['key']
            value = arg['value']
            if type(key) == dict:
                key = self.assign_dict_params(key, value)
                if self.parse_type == 'json':
                    arg['string'] += ',' + re.sub('(^\{|\}$| )', '', str(key).replace("'", "\""))
                else:
                    for k,v in key.items():
                        arg['string'] += k + self.param_bind_char + str(v).replace(' ','')
            else:
                if self.parse_type == 'json':
                    if value == 'null':
                        arg['string'] += ",\""+key+"\":"+value+""
                    else:
                        arg['string'] += ",\""+key+"\":\""+urllib2.quote(value)+"\""
                else:
                    arg['string'] += key + self.param_bind_char + urllib2.quote(value)
            


    def build_string(self):
        self.build_prototype_string()
        for e in ('args', 'options'):
            self.build_arg_string(e)
       
        string = ''
        if 'prototype' in self.query_elements:
            string += self.query_elements['prototype']['string']
            if self.parse_type != 'json':
                string += self.param_chain_char
        if 'args' in self.query_elements:
            for num, arg in enumerate(self.query_elements['args']):
                string += arg['string']
                if self.parse_type != 'json' and len(self.query_elements['args']) > 0:
                    if num < len(self.query_elements['args']):
                        string += self.param_chain_char
        if 'options' in self.query_elements:
            for num, option in enumerate(self.query_elements['options']):
                string += option['string']
                if self.parse_type != 'json' and len(self.query_elements['options']) > 0:
                    if num < len(self.query_elements['options']):
                        string += self.option_chain_char

        if self.parse_type == 'json':
            self.query_string = self.url + self.path + '{' + string + '}'
        else:
            self.query_string = (self.url + self.path + 
                                 string.rstrip(self.option_chain_char).
                                        rstrip(self.param_chain_char))

        #print '\n' + self.query_string + '\n'
        

    def assign_list_params(self, param_list, value):
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
        

    def assign_dict_params(self, param_dict, value):
        for param, entry in param_dict.items():            
            if type(entry) == str:
                if self.multi_value:
                    value = re.sub('(?<!\\\\)\|', self.multi_bind_char, value)
                param_dict[param] += urllib2.quote(str(value))
                param_dict[param] = param_dict[param].lstrip(' ').rstrip(' ')
                return param_dict
            elif type(entry) == list:
                param_dict[param] = self.assign_list_params(entry, value)
                return param_dict
            else:
                param_dict[param] = self.assign_dict_params(entry, value)
                return param_dict


    def parse_prototype(self, arg, value):
        if 'parameters' not in self.prototype:
            raise Exception('Invalid prototype \''+self.prototype+'\'')
        path, entry = self.find_param(arg, self.prototype['parameters'])
        if entry is None:
            raise Exception('Invalid parameter \''+str(arg)+'\'')
        root = path[0]
        
        if 'mode' in entry:
            if entry['mode'] == 'field':
                path, entry = self.find_param(value, entry)
                if not entry:
                    raise Exception('Invalid parameter \''+str(value)+'\'')                
                self.query_elements['args'].append({'key': root, 
                                                    'value': entry})
                return

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
                
        if root == 'options':
            self.query_elements['options'].append({'key': entry, 'value': value})
        else:
            self.query_elements['args'].append({'key': key, 
                                                'value': value})

    def parse_input_options(self):
        self.query_elements['options'] = []
        for elements in self.input_options:
            arg = elements[:-1]
            value = [elements[-1],][0]
            path, entry = self.find_param(arg, self.options)            
            if not entry:
                    raise Exception('Invalid parameter \''+str(arg)+'\'')                
            self.query_elements['options'].append({'key': entry, 'value': value})


    def parse_input_elements(self):
        self.query_elements['args'] = []
        for elements in self.input_elements:

            arg = elements[:-1]
            value = [elements[-1],][0]

            if self.params is None:
                self.query_elements['args'].append({'key':'', 'value':value})
                continue
            
            if len(arg) == 1 and arg[0] == '' and self.lazy_key is not None:
                self.query_elements['args'].append({'key': self.lazy_key,
                                                    'value': value})
                continue
            
            if self.prototype:
                self.parse_prototype(arg, value)
            else:
                path, entry = self.find_param(arg, self.params)            
                root = path[0]                

                if not entry:
                    raise Exception('Invalid parameter \''+str(arg)+'\'')                
                
                if 'mode' in self.params[root]:
                    mode = self.params[root]['mode']
                else:
                    mode = self.params['mode']
                
                if mode == 'field':
                    if type(entry) is list:
                        entry = entry[-1]
                    self.query_elements['args'].append({'key':entry, 'value':value})

                elif mode == 'prototype':                    
                    path, proto_entry = self.find_param((value,), entry)

                    if not proto_entry:
                        raise Exception('Invalid prototype \''+str(value)+'\'')
                    proto_param = path[0]
                    self.prototype = proto_entry

                    if 'key' in entry:
                        key = entry['key']
                    else:
                        key = proto_entry['key']
                   
                    self.query_elements['prototype'] = {'key': key, 
                                                        'value': proto_param}           
        ##print '\n' + str(self.query_elements)
        
    
    def find_param(self, args, params):        
        if type(args) == str:
            args = [args,]
        path = []
        entry = None
        for arg in args:
            arg = re.escape(arg)
            entry = self.search_entries(arg, params)
            if entry:
                if type(entry) == list:
                    p = entry.pop(0)
                    if type(p) == str:
                        p = [p]
                    if p not in path:
                        path = p
                    entry = entry[0]                    
        if entry is not None:
            return [path, entry]
        return [None, None]


    def search_entries(self, arg, params):
        if params == []:
            params = list
        match = None
        if type(params) == dict:
            match = self.find_dict_entry(arg, params)
        elif type(params) in (list, tuple):
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
                    if type(match) == list:
                        path = [param, match.pop(0)]
                        match = match[-1]
                    elif type(match) == str:
                        path = param
                    return [path, match]
        return None


    def find_list_entry(self, arg, params):
        for param in params:
            if type(param) == dict:
                match = self.find_dict_entry(arg, param)        
                if match:
                    path, entry = match
                    return [path, entry]
            elif type(param) in (list, tuple):
                match = self.find_list_entry(arg, param)
                if entry:
                    path, entry = match
                    return [path, param]
            else:
                match = re.match('^(?i)'+arg+'$', param)
                if match:
                    return param
    

    def return_dict_entry(self, arg, params):
        for param, entry in params.items():
            match = re.match('^(?i)'+arg+'$', param)
            if match:
                return entry
            else:
                match = self.get_param_entry(arg, entry)
                if match:
                    return match
        return False


    def return_list_entry(self, arg, list):
        for item in list:
            if type(item) == dict:
                match = self.return_dict_entry(arg, item)
                if match:
                    return match
            else:
                match = re.match('^(?i)'+arg+'$', item)
                if match:
                    return item


    def create_query_object(self, input_string, source, api):
        query_class = type(source['namespace'], (Bibs,), {})
        query_object = query_class()
        query_object.url = source['url']
        query_object.api = api
        query_object.path = source['api'][api]['path']
        query_object.parse_type = source['api'][api]['input']['type']
        query_object.prototype = None
        query_object.input_string = input_string
        query_object.input_elements = []
        query_object.input_options = []
        query_object.query_string = ''
        query_object.query_elements = {}
        query_object.params = source['api'][api]['input']['params']
        query_object.options = source['api'][api]['input']['options']
        
        if 'param_bind_chain' in source['api'][api]['input']:
            query_object.param_bind_char   = source['api'][api]['input']['param_bind_chain'][0]
            query_object.param_chain_char  = source['api'][api]['input']['param_bind_chain'][1]
        else:
            query_object.param_bind_char   = None
            query_object.param_chain_char  = None

        if 'option_bind_chain' in source['api'][api]['input']:
            query_object.option_bind_char  = source['api'][api]['input']['option_bind_chain'][0]
            query_object.option_chain_char = source['api'][api]['input']['option_bind_chain'][1]
        else:
            query_object.option_bind_char  = None
            query_object.option_chain_char = None
            
        if 'multi_value' in source['api'][api]['input']:
            query_object.multi_value      = source['api'][api]['input']['multi_value']
            query_object.multi_bind_char  = source['api'][api]['input']['multi_bind_chain'][0]
            query_object.multi_chain_char = source['api'][api]['input']['multi_bind_chain'][1]
        else:
            query_object.multi_value = False
            query_object.multi_bind_char  = None
            query_object.multi_chain_char = None

        if 'lazy_key' in source['api'][api]['input']:
            query_object.lazy_key = source['api'][api]['input']['lazy_key']
        else:
            query_object.lazy_key = None

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


    
