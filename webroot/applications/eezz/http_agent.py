# -*- coding: utf-8 -*-
"""
    EezzServer:
    High speed application development and
    high speed execution based on HTML5

    Copyright (C) 2023  Albert Zedlitz
"""
import json
import uuid
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup, PageElement
from bs4 import Tag
import copy
from itertools import product
from functools import reduce
from itertools import chain
from table     import TTable, TTableCell, TTableRow
from websocket import TWebSocketAgent
from service   import TService
from lark      import Lark, Transformer, Tree, UnexpectedCharacters


class TEezzAttrTransformer(Transformer):
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


class TDirView(TTable):
    """ Example class """
    def __init__(self, path: str):
        # noinspection PyArgumentList
        super().__init__(column_names=['Path', 'File'])

        a_path = Path.cwd()
        self.column_names = ['Path', 'Files']
        self.table_title = 'Directory'
        self.table_attrs = {'path': a_path}

        for x in a_path.iterdir():
            self.append([str(x.parent), str(x.name)], attrs={'is_dir': x.is_dir()})


class THttpAgent(TWebSocketAgent):
    """ Agent handles WEB socket events """
    def __init__(self):
        super().__init__()
        self.table_tag: Tag | None = None
        self.table_view = TDirView(path='')
        self.m_path     = Path.cwd()

    def handle_request(self, request_data: dict) -> str:
        """ Handle WEB socket requests """
        x_updates = list()
        if 'initialize' in request_data:
            # store {ID : (html, TTable) }
            x_soup    = BeautifulSoup(request_data['initialize'], 'html.parser', multi_valued_attributes=None)
            x_updates.extend([self.generate_html_table(x)  for x in  x_soup.css.select('table[data-eezz-json]')])
            x_updates.extend([self.generate_html_select(x) for x in  x_soup.css.select('select[data-eezz-json]')] )
            x_result = {'update': x_updates}
            return json.dumps(x_result)

    def handle_download(self, description: str, raw_data: Any) -> str:
        """ Handle file downloads """
        return ""

    def do_get(self, a_resource: Path | str) -> str:
        """ Response to an HTML GET command
        The agent reads the source, compiles the data-eezz sections and adds the web-socket component
        It returns the enriched document
        """
        x_html      = a_resource
        x_service   = TService()
        if isinstance(a_resource, Path):
            with a_resource.open('r', encoding="utf-8") as f:
                x_html = f.read()

        x_parser = Lark.open(str(Path(x_service.resource_path) / 'eezz.lark'))
        x_soup   = BeautifulSoup(x_html, 'html.parser', multi_valued_attributes=None)
        x_templ_path = x_service.resource_path / 'template.html'
        with x_templ_path.open('r') as f:
            x_template = BeautifulSoup(f.read(), 'html.parser', multi_valued_attributes=None)

        x_templ_table = x_template.body.table
        for x_chrom in x_soup.css.select('table[data-eezz]'):
            if not x_chrom.css.select('thead'):
                x_chrom.append(copy.deepcopy(x_templ_table.thead))
            if not x_chrom.css.select('tbody'):
                x_chrom.append(copy.deepcopy(x_templ_table.tbody))
            if not x_chrom.css.select('tfoot'):
                # x_chrom.append(copy.deepcopy(x_temp_table.tfoot))
                pass
            if not x_chrom.has_attr('id'):
                x_chrom['id'] = str(uuid.uuid1())
            # Compile sub-tree using the current table id for events
            self.compile_data(x_parser, x_chrom.css.select('[data-eezz]'), x_chrom['id'])

        # Compiling the reset of the document
        self.compile_data(x_parser, x_soup.css.select('[data-eezz]'), '')
        return x_soup.prettify()

    def compile_data(self, a_parser: Lark, a_tag_list: list, a_id: str) -> None:
        for x in a_tag_list:
            x_data = x.attrs.pop('data-eezz')
            try:
                x_syntax_tree = a_parser.parse(x_data)
                x_transformer = TEezzAttrTransformer(x, a_id)
                x_list_json   = x_transformer.transform(x_syntax_tree)
                x['data-eezz-compiled'] = "ok"
            except UnexpectedCharacters as ex:
                x['data-eezz-compiled'] = f'allowed: {ex.allowed} at {ex.pos_in_stream} \n{x_data}'
                print(f'allowed: {ex.allowed} at {ex.pos_in_stream} \n{x_data}')

    def generate_html_cells(self, a_tag: Tag, a_cell: TTableCell) -> Tag:
        """ The cell attributes distinguish between dictionary json-string and string values
        The json-string values are formatted in place using successive replace
        """
        x_fmt_funct = lambda x: x.format(cell=a_cell) if isinstance(x, str) else x
        x_fmt_attrs = {x_key: x_fmt_funct(x_val) for x_key, x_val in a_tag.attrs.items() if x_key != 'data-eezz-json'}
        x_service   = TService()
        if 'data-eezz-json' in a_tag.attrs:
            x_fmt_json = x_service.format_json(json.loads(a_tag.attrs['data-eezz-json']), x_fmt_funct)
            x_fmt_attrs['data-eezz-json'] = json.dumps(x_fmt_json)

        x_new_tag = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        x_new_tag.string = a_tag.string.format(cell=a_cell)
        return x_new_tag

    def generate_html_rows(self, a_html_cells: list, a_tag: Tag, a_row: TTableRow) -> Tag:
        """ This operation add fixed cells to the table.
        Cells which are not included as template for table data are used to add a constant info to the row"""
        x_fmt_funct = lambda x: x.format(row=a_row) if isinstance(x, str) else x
        x_fmt_attrs = {x_key: x_fmt_funct(x_val) for x_key, x_val in a_tag.attrs.items() if x_key != 'data-eezz-json'}
        x_service    = TService()
        if 'data-eezz-json' in a_tag.attrs:
            x_fmt_json = x_service.format_json(json.loads(a_tag.attrs['data-eezz-json']), x_fmt_funct)
            x_fmt_attrs['data-eezz-json'] = json.dumps(x_fmt_json)

        x_html_cells = [[copy.deepcopy(x)] if not x.has_attr('data-eezz-compiled') else a_html_cells for x in a_tag.css.select('th,td')]
        x_html_cells = list(chain.from_iterable(x_html_cells))
        x_new_tag = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        for x in x_html_cells:
            x_new_tag.append(x)
        return x_new_tag

    def generate_html_options(self, a_tag: Tag, a_row: TTableRow, a_header: TTableRow) -> Tag:
        x_fmt_funct = lambda x: x.format(row=a_row) if isinstance(x, str) else x
        x_fmt_row   = {x: y for x, y in zip(a_header.cells, a_row.cells)}
        x_fmt_attrs = {x_key: x_fmt_funct(x_val) for x_key, x_val in a_opt_tag.attrs.items() if x_key != 'data-eezz-json'}
        x_service    = TService()
        if 'data-eezz-json' in a_tag.attrs:
            x_fmt_json = x_service.format_json(json.loads(a_tag.attrs['data-eezz-json']), x_fmt_funct)
            x_fmt_attrs['data-eezz-json'] = json.dumps(x_fmt_json)

        x_new_tag = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        x_new_tag.string = a_tag.string.format(**x_fmt_row)
        return x_new_tag

    def generate_html_table(self, a_table_tag: Tag) -> dict:
        x_row_template = a_table_tag.css.select('tr[data-eezz-compiled]')
        x_row_viewport = self.table_view.get_visible_rows()
        x_table_header = self.table_view.get_header_row()

        # insert the header, so that we could manage header and body in a single stack
        x_row_viewport.insert(0, x_table_header)

        # Evaluate the range and re-arrange
        x_range       = list(range(2).__reversed__())
        x_range_cells = [[x_row.cells[index] for index in x_range] for x_row in x_row_viewport]
        for x_row, x_cells in zip(x_row_viewport, x_range_cells):
            x_row.cells = x_cells

        # Evaluate match: It's possible to have a template for each row type (header and body):
        x_format_row      = [([x_tag for x_tag in x_row_template if x_tag.has_attr('data-eezz-match') and x_tag['data-eezz-match'] == x_row.type], x_row)
                             for x_row in x_row_viewport]
        x_format_cell     = [(list(product(x_tag[0].css.select('td,th'), x_row.cells)), x_tag[0], x_row)
                             for x_tag, x_row in x_format_row if x_tag]

        # Put all together and create HTML
        x_list_html_cells = [([self.generate_html_cells(x_tag, x_cell) for x_tag, x_cell in x_row_templates], x_tag_tr, x_row)
                             for x_row_templates, x_tag_tr, x_row in x_format_cell]
        x_list_html_rows  = [(self.generate_html_rows(x_html_cells, x_tag_tr, x_row))
                             for x_html_cells, x_tag_tr, x_row in x_list_html_cells]

        # separate header and body again for the result {a_table_tag["id"]}
        x_html = {'thead': '', 'tbody': ''}
        if len(x_list_html_rows) > 0:
            x_html.update({'thead': x_list_html_rows[0]})
        if len(x_list_html_rows) > 1:
            x_html.update({'tbody': ''.join([str(x) for x in x_list_html_rows[1:]])})

        return {'id': a_table_tag["id"], 'attrs': {}, 'html': x_html}

    def generate_html_select(self, a_select_tag: Tag) -> dict:
        x_opt_template     = a_select_tag.css.select('option[data-eezz-json]')
        x_row_viewport     = self.table_view.get_visible_rows()
        x_table_header     = self.table_view.get_header_row()
        x_list_html_option = [self.generate_html_options(x_opt_template, x, x_table_header) for x in x_row_viewport]
        return {'id': a_select_tag['id'], 'attrs': {}, 'html': {
                'option': ''.join([str(x) for x in x_list_html_option])}}


if __name__ == '__main__':
    text2 = """
    <table data-eezz="name: directory, assign: TDirView(path = value)"> </table>
    """

    # list_table = aSoup.css.select('table[data-eezz]')
    TService(root_path=Path('/home/paul/Projects/github/EezzServer2/webroot'))
    xx_gen  = THttpAgent()
    xx_html = xx_gen.do_get(text2)
    xx_soup = BeautifulSoup(xx_html, 'html.parser', multi_valued_attributes=None)

    list_table = xx_soup.css.select('table[data-eezz-compiled]')
    for xx in list_table:
        xx_table = xx_gen.generate_html_table(xx)
        print(xx_table)
