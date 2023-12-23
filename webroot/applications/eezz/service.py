# -*- coding: utf-8 -*-
"""
    EezzServer: 
    High speed application development and 
    high speed execution based on HTML5
    
    Copyright (C) 2015  Albert Zedlitz

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

 
"""
import itertools
import json
import sys
import logging
import threading

from   bs4         import Tag
from   dataclasses import dataclass
from   pathlib     import Path
from   importlib   import import_module
from   lark        import Lark, Transformer, Tree
from   table       import TTable
from   typing      import Dict, Callable
from   threading   import Thread


def singleton(a_class):
    """ Singleton decorator for TService """
    instances = {}

    def get_instance(**kwargs):
        if a_class not in instances:
            instances[a_class] = a_class(**kwargs)
        return instances[a_class]
    return get_instance


@singleton
@dataclass(kw_only=True)
class TService:
    """ Container for environment """
    root_path:        Path = None
    document_path:    Path = None
    application_path: Path = None
    public_path:      Path = None
    resource_path:    Path = None
    locales_path:     Path = None
    host:             str  = 'localhost'
    websocket_addr:   int  = 8100
    global_objects:   dict = None
    post_init_fkt:    list = None
    translate:        bool = False
    async_methods:    Dict[Callable, Thread] = None

    def __post_init__(self):
        if not self.root_path:
            self.root_path = Path('/home/paul/Projects/github/EezzServer2/webroot')
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        self.resource_path    = self.root_path      / 'resources'
        self.public_path      = self.root_path      / 'public'
        self.application_path = self.root_path      / 'applications'
        self.document_path    = self.root_path      / 'database'
        self.locales_path     = self.resource_path  / 'locales'
        self.global_objects   = dict()
        self.post_init_fkt    = list()

    def assign_object(self, obj_id: str, a_descr: str, attrs: dict, a_tag: Tag = None) -> None:
        try:
            x_list  = a_descr.split('.')
            x, y, z = x_list[:-2], x_list[-2], x_list[-1]
        except Exception as ex:
            print(ex)
            logging.error(f'{ex}: Description of an assignment is <Directory>.<Module>.<Class> ')
            return

        x_path = self.application_path / '/'.join(x)

        if not str(x_path) in sys.path:
            sys.path.append(str(x_path))

        try:
            x_module    = import_module(y)
            x_class     = getattr(x_module, z)
            x_object    = x_class(**attrs)
            self.global_objects.update({obj_id: (x_object, a_tag, a_descr)})
        except Exception as ex:
            print(ex)
            logging.error(ex)

    def add_post_init_method(self, obj_id: str, a_method_name: str, args: dict) -> None:
        self.post_init_fkt.append((obj_id, a_method_name, args))

    def get_method(self, obj_id: str, a_method_name: str) -> tuple:
        x_object, x_tag, x_descr = self.global_objects[obj_id]
        x_method = getattr(x_object, a_method_name)
        return x_object, x_method, x_tag

    def get_object(self, obj_id: str) -> TTable:
        x_object, x_tag, x_descr = self.global_objects[obj_id]
        return x_object


class TServiceCompiler(Transformer):
    """ Transforms the parser tree into a list of dictionaries """
    def __init__(self, a_tag: Tag, a_id: str = '', a_query: dict = None):
        super().__init__()
        self.m_id       = a_id
        self.m_tag      = a_tag
        self.m_query    = a_query
        self.m_service  = TService()

        # Generator section
        self.simple_str       = lambda item: ''.join([str(x) for x in item])
        self.escaped_str      = lambda item: ''.join([x.strip('"') for x in item])
        self.qualified_string = lambda item: '.'.join([str(x) for x in item])
        self.list_updates     = lambda item: list(itertools.accumulate(item, lambda a, b: a | b))[-1]
        self.list_arguments   = lambda item: list(itertools.accumulate(item, lambda a, b: a | b))[-1]
        self.update_section   = lambda item: {'update': item[0]}
        self.update_item      = lambda item: {item[0]: item[1]} if len(item) == 2 else {item[0]: item[0]}
        self.assignment       = lambda item: {item[0]: item[1]}
        self.format_string    = lambda item: f'{{{".".join(item)}}}'
        self.format_value     = lambda item: f'{{{".".join([str(x[0]) for x in item[0].children])}}}'

    def template_section(self, item):
        if item[0] in ('name', 'match', 'template'):
            self.m_tag[f'data-eezz-{item[0]}'] = item[1]
        return {item[0]: item[1]}

    def funct_assignment(self, item):
        x_function, x_args = item[0].children
        self.m_tag['onclick'] = 'eezzy_click(event, this)'
        return {'call': {'function': x_function, 'args': x_args, 'id': self.m_id}}

    def post_init(self, item):
        x_function, x_args = item[0].children
        x_json_obj = {'call': {'function': x_function, 'args': x_args, 'id': self.m_id}}
        self.m_tag['data-eezz-init'] = json.dumps(x_json_obj)
        print(self.m_tag)
        return x_json_obj

    def table_assignment(self, item):
        """ The table assignment uses TQuery to format arguments
        In case the arguments are not all present, the format is broken and process continues with default """
        x_function, x_args = item[0].children

        try:
            x_query = TQuery(self.m_query)
            x_args  = {x_key: x_val.format(query=x_query) for x_key, x_val in x_args.items()}
        except AttributeError as ex:
            pass
        self.m_service.assign_object(self.m_id, x_function, x_args, self.m_tag)
        return {'assign': {'function': x_function, 'args': x_args, 'id': self.m_id}}


class TTranslate:
    def __init__(self):
        pass

    @staticmethod
    def generate_pot(self, a_soup, a_title):
        try:
            x_pot_file = TService().locales_path / f'{a_title}.pot'
            x_elements = a_soup.find_all(lambda x_tag: x_tag.has_attr('data-eezz-i18n'))
            x_path_hdr = TService().locales_path / 'template.pot'
            with x_pot_file.open('w', encoding='utf-8') as f:
                with x_path_hdr.open('r', encoding='utf-8') as f_hdr:
                    f.write(f_hdr.read())
                for x_elem in x_elements:
                    f.write(f"msgid  \"{x_elem['data-eezz-i18n']}\"\n"
                            f"msgstr \"{[str(x) for x in x_elem.descendants]}\"\n\n")
        except FileNotFoundError as ex:
            logging.error(f'Creation of POT file is not possible: {str(ex)}')


@dataclass(kw_only=True)
class TQuery:
    """ Data class to perform a format function. Attributes are provided dynamically """
    def __init__(self, query: dict):
        if query:
            for x_key, x_val in query.items():
                setattr(self, x_key, ','.join(x_val))


if __name__ == '__main__':
    xx_sys = TService(root_path='/home/paul/Projects/github/EezzServer2/webroot')
    # #xx_sys.assign_object('1', 'examples.directory.TDirView', {'path': '/home/paul/Projects/github/EezzServer2/webroot'}, None)
    # xx_object, xx_method, xx_tag = xx_sys.get_method("1", 'print')
    #  xx_method()
    # xx_object.print()

    g_parser = Lark.open(str(Path(TService().resource_path) / 'eezz.lark'))
    dataeezz = 'assign: examples.directory.TDirView(path="."),  post_init: find_devices(), update: this.tbody'
    g_syntax_tree = g_parser.parse(dataeezz)
    g_tag         = Tag(name='text')
    g_transformer = TServiceCompiler(g_tag, 'Directory')
    g_list_json = g_transformer.transform(g_syntax_tree)
    if isinstance(g_list_json, Tree):
        print(g_list_json.children)
    print(g_list_json)
