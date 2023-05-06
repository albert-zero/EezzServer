# -*- coding: utf-8 -*-
"""
    EezzServer:
    High speed application development and
    high speed execution based on HTML5

    Copyright (C) 2023  Albert Zedlitz
"""
import json
import threading
import uuid
import copy
import re

from pathlib   import Path
from typing    import Any, Callable
from bs4       import Tag, BeautifulSoup, NavigableString
from itertools import product, chain, filterfalse
from table     import TTable, TTableCell, TTableRow
from websocket import TWebSocketAgent
from service   import TService, TServiceCompiler
from lark      import Lark, UnexpectedCharacters


class THttpAgent(TWebSocketAgent):
    """ Agent handles WEB socket events """
    def __init__(self):
        super().__init__()

    def handle_request(self, request_data: dict) -> str:
        """ Handle WEB socket requests """
        x_updates  = list()
        if 'initialize' in request_data:
            x_soup   = BeautifulSoup(request_data['initialize'], 'html.parser', multi_valued_attributes=None)
            x_updates.extend([self.generate_html_table(x) for x in  x_soup.css.select('table[data-eezz-compiled]')])
            x_updates.extend([self.generate_html_grid(x)  for x in  x_soup.css.select('select[data-eezz-compiled], .clzz_grid[data-eezz-compiled]')] )
            x_result = {'update': x_updates}
            return json.dumps(x_result)
        if 'event' in request_data:
            try:
                x_event = request_data['event']
                x_obj, x_method, x_tag  = TService().get_method(x_event['id'], x_event['function'])
                x_res   = x_method(**x_event['args'])

                for x_key, x_value in x_event['update'].items():
                    if x_key == 'this.tbody':
                        x_updates.append(self.generate_html_table(x_tag))
                    elif x_key == 'this':
                        x_updates.append(self.generate_html_grid(x_tag))
                    elif x_value.startswith('table.'):
                        x_attr_list = x_key.split('.')
                        x_attr      = '.' if len(x_attr_list) < 2 else '.'.join(x_attr_list[1:])
                        x_res_v     = f'{{{x_value}}}'.format(table=x_obj)
                        x_res_d     = {'id': x_attr_list[0], 'attrs': {'result': x_res}, 'html': {x_attr: x_res_v}}
                        x_updates.append(x_res_d)
                    elif re.match(r'"\w+"', x_value):
                        x_attr_list = x_key.split('.')
                        x_attr      = '.' if len(x_attr_list) < 2 else '.'.join(x_attr_list[1:])
                        x_res_d     = {'id': x_attr_list[0], 'attrs': {'result': x_res}, 'html': {x_attr: x_value.strip('"')}}
                        x_updates.append(x_res_d)
            except KeyError as ex:
                print(f'key-error in handle_request: {request_data} ')

            x_result = {'update': x_updates}
            return json.dumps(x_result)

    def handle_download(self, description: str, raw_data: Any) -> str:
        """ Handle file downloads """
        with self.m_lock:
            return ""

    def do_get(self, a_resource: Path | str) -> str:
        """ Response to an HTML GET command
        The agent reads the source, compiles the data-eezz sections and adds the web-socket component
        It returns the enriched document
        """
        x_html    = a_resource
        x_service = TService()
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
            if not x_chrom.css.select('caption'):
                x_chrom.append(copy.deepcopy(x_templ_table.caption))
            if not x_chrom.css.select('thead'):
                x_chrom.append(copy.deepcopy(x_templ_table.thead))
            if not x_chrom.css.select('tbody'):
                x_chrom.append(copy.deepcopy(x_templ_table.tbody))
            if not x_chrom.css.select('tfoot'):
                # x_chrom.append(copy.deepcopy(x_temp_table.tfoot))
                pass
            if not x_chrom.has_attr('id'):
                x_chrom['id'] = str(uuid.uuid1())[:8]
            # Compile sub-tree using the current table id for events
            self.compile_data(x_parser, x_chrom.css.select('[data-eezz]'), x_chrom['id'])

        for x_chrom in x_soup.css.select('select[data-eezz], .clzz_grid[data-eezz]'):
            if not x_chrom.has_attr('id'):
                x_chrom['id'] = str(uuid.uuid1())[:8]
            self.compile_data(x_parser, x_chrom.css.select('[data-eezz]'), x_chrom['id'])

        # Compiling the reset of the document
        self.compile_data(x_parser, x_soup.css.select('[data-eezz]'), '')
        return x_soup.prettify()

    def compile_data(self, a_parser: Lark, a_tag_list: list, a_id: str) -> None:
        """ Compile data-eezz-json to data-eezz-compile,
        create tag attributes and generate tag-id to manage incoming requests """
        x_service = TService()
        for x in a_tag_list:
            x_id   = a_id
            x_data = x.attrs.pop('data-eezz')
            try:
                if not x_data:
                    return
                if not x_id:
                    if x.has_attr('id'):
                        x_id = x.attrs['id']
                # else:
                #    return

                x_syntax_tree = a_parser.parse(x_data)
                x_transformer = TServiceCompiler(x, x_id)
                x_list_json   = x_transformer.transform(x_syntax_tree)
                x['data-eezz-compiled'] = "ok"
                if x.has_attr('data-eezz-template') and x['data-eezz-template'] == 'websocket':
                    x_path      = Path(x_service.resource_path / 'websocket.js')
                    x_ws_descr  = """var g_eezz_socket_addr = "ws://{host}:{port}";\n """.format(host=TService().host, port=TService().websocket_addr, args='')
                    x_ws_descr += """var g_eezz_arguments   = "{args}";\n """.format(args='')
                    with x_path.open('r') as f:
                        x_ws_descr += f.read()
                    x.string = x_ws_descr
            except UnexpectedCharacters as ex:
                x['data-eezz-compiled'] = f'allowed: {ex.allowed} at {ex.pos_in_stream} \n{x_data}'
                print(f'allowed: {ex.allowed} at {ex.pos_in_stream} \n{x_data}')

    def format_attributes(self, a_key: str, a_value: str, a_fmt_funct: Callable) -> str:
        """ Eval template tag-attributes, diving deep into data-eezz-json """
        if a_key == 'data-eezz-json':
            x_json = json.loads(a_value)
            x_json.update({'args': {x: a_fmt_funct(y) for x, y in x_json['args'].items()}})
            x_fmt_val = json.dumps(x_json)
        else:
            x_fmt_val = a_fmt_funct(a_value)
        return x_fmt_val

    def generate_html_cells(self, a_tag: Tag, a_cell: TTableCell) -> Tag:
        """ Generate HTML cells """
        x_fmt_attrs = {x: self.format_attributes(x, y, lambda z: z.format(cell=a_cell)) for x, y in a_tag.attrs.items()}
        x_new_tag   = copy.deepcopy(a_tag)
        for x in x_new_tag.descendants:
            if x and isinstance(x, Tag):
                x.string = x.string.format(cell=a_cell)
        if x_new_tag.string:
            x_new_tag.string = a_tag.string.format(cell=a_cell)
        x_new_tag.attrs  = x_fmt_attrs

        # store the date-time in attribute, so it could be used for in-place formatting:
        if a_cell.type in ('datetime', 'date', 'time'):
            x_new_tag['timestamp'] = str(a_cell.value.timestamp())
        return x_new_tag

    def generate_html_rows(self, a_html_cells: list, a_tag: Tag, a_row: TTableRow) -> Tag:
        """ This operation add fixed cells to the table.
        Cells which are not included as template for table data are used to add a constant info to the row"""
        x_fmt_attrs  = {x: self.format_attributes(x, y, lambda z: z.format(row=a_row)) for x, y in a_tag.attrs.items()}
        # x_html_cells = a_html_cells
        x_html_cells = [[copy.deepcopy(x)] if not x.has_attr('data-eezz-compiled') else a_html_cells for x in a_tag.css.select('th,td')]
        x_html_cells = list(chain.from_iterable(x_html_cells))
        x_new_tag    = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        for x in x_html_cells:
            x_new_tag.append(x)
        return x_new_tag

    def generate_html_table(self, a_table_tag: Tag) -> dict:
        """ Generates a table structure in four steps
        1. Get the column order and the viewport
        2. Get the row templates
        3. Evaluate the table cells
        4. Send the result separated by table main elements """
        x_table_obj    = TService().get_object(a_table_tag.attrs['id'])
        x_row_template = a_table_tag.css.select('tr[data-eezz-compiled]')
        x_row_viewport = x_table_obj.get_visible_rows()
        x_table_header = x_table_obj.get_header_row()

        # insert the header, so that we could manage header and body in a single stack
        x_row_viewport.insert(0, x_table_header)

        # Evaluate the range and re-arrange
        x_range       = list(range(len(x_table_header.cells)))
        x_range_cells = [[x_row.cells[index] for index in x_range] for x_row in x_row_viewport]
        for x_row, x_cells in zip(x_row_viewport, x_range_cells):
            x_row.cells = x_cells

        # Evaluate match: It's possible to have a template for each row type (header and body):
        x_format_row      = [([x_tag for x_tag in x_row_template if x_tag.has_attr('data-eezz-match') and x_tag['data-eezz-match'] in x_row.type], x_row) for x_row in x_row_viewport]
        x_format_cell     = [(list(product(x_tag[0].css.select('td[data-eezz-compiled],th[data-eezz-compiled]'), x_row.cells)), x_tag[0], x_row) for x_tag, x_row in x_format_row if x_tag]

        # Put all together and create HTML
        x_list_html_cells = [([self.generate_html_cells(x_tag, x_cell) for x_tag, x_cell in x_row_templates], x_tag_tr, x_row) for x_row_templates, x_tag_tr, x_row in x_format_cell]
        x_list_html_rows  = [(self.generate_html_rows(x_html_cells, x_tag_tr, x_row)) for x_html_cells, x_tag_tr, x_row in x_list_html_cells]

        # separate header and body again for the result {a_table_tag["id"]}
        x_html = dict()
        x_html['caption'] = a_table_tag.caption.string.format(table=x_table_obj)
        x_html['thead']   = str(x_list_html_rows[0]) if x_list_html_rows else ''
        x_html['tbody']   = ''.join([str(x) for x in x_list_html_rows[1:]]) if len(x_list_html_rows) > 1 else ''

        return {'id': a_table_tag["id"], 'attrs': {}, 'html': x_html}

    def generate_html_grid(self, a_tag: Tag) -> dict:
        """ Besides the table, supported display is grid (via class clzz_grid or select """
        x_template      = a_tag.css.select('select[data-eezz-compiled], .clzz_grid[data-eezz-compiled]')
        x_table         = TService().get_object(a_tag.attrs['id'])
        x_row_viewport  = x_table.get_visible_rows()
        x_table_header  = x_table.get_header_row()
        x_list_children = [self.generate_html_grid_item(x_template, x, x_table_header) for x in x_row_viewport]
        return {'id': a_tag['id'], 'attrs': {}, 'html': {'.': ''.join([str(x) for x in x_list_children])}}

    def generate_html_grid_item(self, a_tag: Tag, a_row: TTableRow, a_header: TTableRow) -> Tag:
        """ Generates elements of the same kind, derived from a template and update content
        according the row values """
        x_fmt_attrs = {x: self.format_attributes(x, y, lambda z: z.format(roe=a_row)) for x, y in a_tag.attrs.items()}
        x_fmt_row   = {x: y for x, y in zip(a_header.cells, a_row.cells)}
        x_new_tag   = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        x_new_tag.string = a_tag.string.format(**x_fmt_row)
        return x_new_tag


if __name__ == '__main__':
    text2 = """
    <h1>>header</h1>
    <table data-eezz='name: directory, assign: examples.directory.TDirView(path="/home/paul")'> </table>
    
    <div class="clzz_grid" data-eezz=""></div>
    """

    # list_table = aSoup.css.select('table[data-eezz]')
    TService(root_path=Path('/home/paul/Projects/github/EezzServer2/webroot'))
    xx_gen  = THttpAgent()
    xx_html = xx_gen.do_get(text2)
    xx_soup = BeautifulSoup(xx_html, 'html.parser', multi_valued_attributes=None)

    xx_h1_set = xx_soup.css.select('h1')
    xx_h1     = xx_h1_set[0]
    xx_str    = xx_h1.string
    print(xx_str.parent)

    list_table = xx_soup.css.select('table[data-eezz-compiled]')
    for xx in list_table:
        xx_table = xx_gen.generate_html_table(xx)
        print(xx_table)

        xx_result = {'update': [xx_table]}
        xx_str    = json.dumps(xx_result)
        print(xx_str)

    print('done')