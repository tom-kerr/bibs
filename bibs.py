import os, sys
import glob
import urllib2, urllib
import yaml, json
import re

class Bibs:

    source_dir = 'sources/'

    def __init__(self):
        self.load_sources()


    def load_sources(self):
        self.sources = {}
        source_list = glob.glob(Bibs.source_dir + '*.yaml')
        for source in source_list:
            try:
                f = open(source, 'r')
                y = yaml.load(f)
                self.sources[y['namespace']] = y
            except Exception as e:
                raise Exception(str(e))

    
    def get_source(self, source):
        if source is not None and source in self.sources:
            return source, self.sources[source]
        else:
            for s, specs in self.sources.items():
                if specs['default']:
                    return specs['namespace'], self.sources[s]


    def search(self, query, source=None, api='default'):
        ns, search_source = self.get_source(source)
        input_type = search_source['api'][api]['input']['type']        
        if input_type == 'json':
            query_string = self.format_as_json(query, search_source, api)
        elif input_type == 'key_value':
            query_string = self.format_as_key_value(query, search_source, api)
        elif input_type == 'lazy_key_value':
            query_string = self.format_lazy(query, search_source, api)
        #print query_string
        #return
        request = urllib2.urlopen(query_string)
        results = request.read()
        return json.loads(results)
        #return results


    def get_param(self, element, params):
        for param in params:
            if type(param) == dict:
                for key, value  in param.items():
                    match = re.search('(?i)'+element, key)
                    if match:
                        return param
            else:
                match = re.search('(?i)'+element, param)
                if match:
                    return param
        return False


    def format_lazy(self, query, source, api):
        elements = query.split(':')
        param_bind_char, param_chain_char = source['api'][api]['input']['param_bind_chain']
        option_bind_char, option_chain_char = source['api'][api]['input']['option_bind_chain']
        if len(elements) == 1:
            return source['url'] + source['api'][api]['path'] + param_bind_char + urllib2.quote(query)
        else:
            query_string = ''
            for num in range(0, len(elements), 2):
                key, value = elements[num], elements[num + 1]
                query_string += str(key) + str(option_bind_char) + urllib2.quote(value)
                if num != len(elements) - 2:
                    query_string += str(option_chain_char)
        return source['url'] + source['api'][api]['path'] + query_string


    def format_as_key_value(self, query, source, api):
        elements = query.split(':')
        if len(elements)%2!=0:
            raise Exception('Invalid query: Not enough arguments.')
        param_bind_char, param_chain_char = source['api'][api]['input']['param_bind_chain']
        option_bind_char, option_chain_char = source['api'][api]['input']['option_bind_chain']
        query_string = ''
        for num in range(0, len(elements), 2):
            key, value = elements[num], elements[num + 1]
            param = self.get_param(key, source['api'][api]['input']['params'])
            if param:
                query_string += str(param) + str(param_bind_char) + urllib2.quote(value) + str(param_chain_char)
                continue
            param = self.get_param(key, source['api'][api]['input']['options'])
            if param:
                query_string += str(option_chain_char) + str(param) + str(option_bind_char) + urllib2.quote(value)
                continue
            else:
                raise Exception('Invalid query: \''+str(key)+'\' unknown parameter.')
        return source['url'] + source['api'][api]['path'] + query_string
                                                                    

    def format_as_json(self, query, source, api):
        elements = query.split(':')
        qtype = self.get_param(elements[0], source['api'][api]['input']['params'])
        if not qtype:
            raise Exception('Invalid query: \''+str(qtype)+'\' unknown parameter.')
        elements = elements[1:]
        if len(elements)%2!=0:
            raise Exception('Invalid query: Not enough arguments.')
        qproperties = []
        qstrings = []
        property_items = []
        for num in range(0, len(elements), 2):
            key, value = elements[num], elements[num+1]
            param = self.get_param(key, source['api'][api]['input']['params'][qtype])
            print param
            if type(param) == tuple:
                property_items.append((param, urllib2.quote(value)))
            elif type(param) == dict:
                param_dict = self.assign_params(param, value)
                property_items.append(param_dict)
            else:
                raise Exception('Invalid query: \''+qproperty+'\' unknown property')
        query_string = "{\"type\":\"\/type\/" + qtype + "\""
        for item in property_items:
            if type(item) == tuple:
                query_string += ",\""+item[0]+"\":\""+item[1]+"\""
            elif type(item) == dict:
                query_string += ',' + re.sub('(^\{|\}$)', '', str(item).replace("'", "\""))
        query_string = str(source['url']) + str(source['api'][api]['path']) + urllib2.quote(query_string + '}')
        return query_string


    def assign_params(self, param_dict, value):
        for param, dictionary in param_dict.items():
            for key, pair in dictionary.items():
                pair['key'] = '/' + param + '/' + value
        return param_dict
        


        

