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
from   bs4         import Tag
from   dataclasses import dataclass
from   pathlib     import Path
from   importlib   import import_module
import sys
from   lark        import Lark, Transformer, Tree
from   table       import TTable
from   threading   import Condition
import logging

def singleton(a_class):
    """ Singleton decorator """
    instances = {}

    def get_instance(**kwargs):
        if a_class not in instances:
            instances[a_class] = a_class(**kwargs)
        return instances[a_class]
    return get_instance


@singleton
@dataclass(kw_only=True)
class TService:
    root_path:        Path = None
    document_path:    Path = None
    application_path: Path = None
    public_path:      Path = None
    resource_path:    Path = None
    locales_path:     Path = None
    host:             str  = 'localhost'
    websocket_addr:   int  = 8100
    global_objects:   dict = None
    condition:        Condition = None
    translate:        bool = False

    def __post_init__(self):
        if not self.root_path:
            self.root_path = Path('/home/paul/Projects/github/EezzServer2/webroot')
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        self.condition        = Condition()
        self.resource_path    = self.root_path / 'resources'
        self.public_path      = self.root_path / 'public'
        self.application_path = self.root_path / 'applications'
        self.document_path    = self.root_path / 'database'
        self.locales_path     = self.resource_path / 'locales'
        self.global_objects   = {}

    def assign_object(self, obj_id: str, a_descr: str, attrs: dict, a_tag: Tag = None) -> None:
        x, y, z = a_descr.split('.')
        x_path = self.application_path / x

        if not str(x_path) in sys.path:
            sys.path.append(str(x_path))

        try:
            x_module = import_module(y)
            x_class  = getattr(x_module, z)
            x_object = x_class(condition=self.condition, **attrs)
            self.global_objects.update({obj_id: (x_object, a_tag)})
        except Exception as ex:
            print(ex)

    def get_method(self, obj_id: str, a_method_name: str) -> tuple:
        x_object, x_tag = self.global_objects[obj_id]
        x_method = getattr(x_object, a_method_name)
        return x_object, x_method, x_tag

    def get_object(self, obj_id: str) -> TTable:
        x_object, x_tag = self.global_objects[obj_id]
        return x_object


class TServiceCompiler(Transformer):
    """ Transforms the parser tree into a list of dictionaries """
    def __init__(self, a_tag: Tag, a_id: str = '', a_query: dict = None):
        super().__init__()
        self.m_id    = a_id
        self.m_tag   = a_tag
        self.m_query = a_query

    def template_section(self, item):
        if item[0] in ('name', 'match', 'template'):
            self.m_tag[f'data-eezz-{item[0]}'] = item[1]
        return {item[0]: item[1]}

    def simple_str(self, item):
        x_str = ''.join([str(x) for x in item])
        return x_str

    def escaped_str(self, item):
        x_str = ''.join([x.strip('"') for x in item])
        return x_str

    def format_string(self, item):
        x_str = '.'.join(item)
        return f'{{{x_str}}}'

    def update_item(self, item):
        x_key, x_value = item
        return {x_key: x_value}

    def list_updates(self, item):
        x_result = dict()
        for x in item:
            x_result.update(x)
        return x_result

    def update_section(self, item):
        x_args         = item[0]
        return {'update': x_args}

    def assignment(self, item):
        x_key, x_value = item
        return {x_key: x_value}

    def list_arguments(self, item):
        """ Concatenate the argument list for function calls """
        x_result = dict()
        for x in item:
            x_result.update(x)
        return x_result

    def qualified_string(self, item):
        x_tree = item[0]
        return '.'.join([x for x in item])

    def format_value(self, item):
        """ Concatenate a qualified string """
        x_tree = item[0]
        x_str = '.'.join([str(x[0]) for x in x_tree.children])
        return f"{{{x_str}}}"

    def async_section(self, item):
        x_function, x_args = item[0].children
        return {'call': {'function': x_function, 'args': x_args, 'id': self.m_id, 'type': 'async'}}

    def funct_assignment(self, item):
        x_function, x_args = item[0].children
        self.m_tag['onclick'] = 'eezy_click(event, this)'
        return {'call': {'function': x_function, 'args': x_args, 'id': self.m_id, 'type': 'update'}}

    def table_assignment(self, item):
        """ The table assignment uses TQuery to format arguments
        In case the arguments are not all present, the format is broken and process continues with default """
        x_function, x_args = item[0].children
        try:
            x_query = TQuery(self.m_query)
            x_args  = {x_key: x_val.format(query=x_query) for x_key, x_val in x_args.items()}
        except AttributeError as ex:
            pass
        TService().assign_object(self.m_id, x_function, x_args, self.m_tag)
        return {'call': {'function': x_function, 'args': x_args, 'type': 'assign'}}


class TTranslate:
    def __init__(self):
        pass

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
    xx_sys.assign_object('1', 'examples.directory.TDirView', {'path': '/home/paul/Projects/github/EezzServer2/webroot'}, None)
    xx_object, xx_method, xx_tag = xx_sys.get_method("1", 'print')
    # xx_method()
    xx_object.print()

    g_parser = Lark.open(str(Path(TService().resource_path) / 'eezz.lark'))
    dataeezz = 'assign: examples.directory.TDirView(path="."), name: Directory'
    g_syntax_tree = g_parser.parse(dataeezz)
    g_tag         = Tag(name='text')
    g_transformer = TServiceCompiler(g_tag, '1000')
    g_list_json = g_transformer.transform(g_syntax_tree)
    if isinstance(g_list_json, Tree):
        print(g_list_json.children)
    print(g_list_json)
