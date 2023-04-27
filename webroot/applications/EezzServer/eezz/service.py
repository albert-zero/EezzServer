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
from dataclasses import dataclass
from pathlib     import Path
from lark        import Transformer

def singleton(a_class):
    """ Singleton decorator """
    instances = {}

    def get_instance():
        if a_class not in instances:
            instances[a_class] = a_class()
        return instances[a_class]
    return get_instance


@singleton
@dataclass(kw_only=True)
class TService:
    root_path:        Path | None = None
    document_path:    Path | None = None
    application_path: Path | None = None
    public_path:      Path | None = None
    resource_path:    Path | None = None

    def __post_init__(self):
        if not self.root_path:
            self.root_path = Path('/home/paul/Projects/github/EezzServer2/webroot')
        self.resource_path    = self.root_path / 'resources'
        self.public_path      = self.root_path / 'public'
        self.application_path = self.root_path / 'applications'
        self.document_path    = self.root_path / 'database'

    def format_json(self, a_json: dict, a_fmt):
        for x, y in a_json.items():
            if isinstance(y, dict):
                self.format_json(y, a_fmt)
            else:
                a_json.update({x: a_fmt(y)})
        return a_json



