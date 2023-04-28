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
from   lark        import Transformer
import json


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
    root_path:        Path
    document_path:    Path | None = None
    application_path: Path | None = None
    public_path:      Path | None = None
    resource_path:    Path | None = None

    def __post_init__(self):
        if not self.root_path:
            self.root_path = Path('/home/paul/Projects/github/EezzServer2/webroot')
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        self.resource_path    = self.root_path / 'resources'
        self.public_path      = self.root_path / 'public'
        self.application_path = self.root_path / 'applications'
        self.document_path    = self.root_path / 'database'

    def dynamic_call(self):
        x_package_name = 'examples'
        x_module_name  = 'directory'
        x_class_name   = 'TDirView'
        x_method_name  = 'print'
        sys.path.append(str(self.application_path / x_package_name))
        x_module  = import_module(x_module_name)
        x_class   = getattr(x_module, x_class_name)
        x_object  = x_class(path='/')
        x_method  = getattr(x_object, x_method_name)
        x_method()
        pass


class TServiceCompiler(Transformer):
    """ Transforms the parser tree into a list of dictionaries """
    def __init__(self, a_tag: Tag, a_id: str = ''):
        super().__init__()
        self.m_id  = a_id
        self.m_tag = a_tag

    def template_section(self, item):
        if item[0] in ('name', 'match'):
            self.m_tag[f'data-eezz-{item[0]}'] = item[1]
        return {item[0]: item[1]}

    def simple_str(self, item):
        x_str = ''.join([str(x) for x in item])
        return x_str

    def format_string(self, item):
        x_str = '.'.join(item)
        return f'{{{x_str}}}'

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
        return '.'.join([str(x[0]) for x in x_tree.children])

    def format_value(self, item):
        """ Concatenate a qualified string """
        x_tree = item[0]
        x_str = '.'.join([str(x[0]) for x in x_tree.children])
        return f"{{{x_str}}}"

    def funct_assignment(self, item):
        x_function, x_args = item[0].children
        self.m_tag[f'data-eezz-json'] = json.dumps({'event': 'assign', 'function': x_function, 'args': x_args, 'id': self.m_id})
        return {'function': x_function, 'args': x_args, 'id': self.m_id}

    def table_assignment(self, item):
        x_function, x_args = item[0].children
        self.m_tag[f'data-eezz-json'] = json.dumps({'event': 'onselect', 'function': x_function, 'args': x_args})
        return {'assign': x_function, 'args': x_args}


if __name__ == '__main__':
    xsys = TService(root_path='/home/paul/Projects/github/EezzServer2/webroot')
    xsys.dynamic_call()

    print(xsys.root_path)
