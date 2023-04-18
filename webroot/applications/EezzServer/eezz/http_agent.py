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
from bs4 import BeautifulSoup, PageElement
from bs4 import Tag
import copy
from itertools import product
from functools import reduce
from itertools import chain
from table     import TTable, TTableCell, TTableRow


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


class THttpAgent:
    def __init__(self):
        self.table_tag: Tag | None = None
        self.table_view = TDirView(path='')

    def generate_html_table(self, a_table_tag: Tag) -> Tag:
        """ Expands the templates of a user tree """
        self.table_tag = a_table_tag

        x_tree_list = ['thead', 'tr', 'th', None, None, None, 'tbody', 'tr', 'td', None, None, None, 'tfoot', None]
        reduce(self.check_structure, x_tree_list, a_table_tag)

        self.compile_data(a_table_tag)
        for x in a_table_tag.descendants:
            if isinstance(x, Tag) and x.has_attr('data-eezz'):
                self.compile_data(x)

        # At this point the structure is ready to store for successive update.
        # Store the table and associated object in global:
        # a_gloabal  = {'name': (a_table_tag, TDirView('')) }
        x_template       = self.expand_table_segments(a_table_tag)
        x_template['id'] = a_table_tag['id']
        return x_template

    def check_structure(self, a_tag: Tag, a_tag_name: str) -> Tag:
        """ prepare the table skeleton, creating missing elements """
        if not a_tag_name:
            return a_tag.parent

        x_tag = a_tag.css.select(a_tag_name)
        if x_tag:
            return x_tag[0]

        x_new_tag = Tag(name=a_tag_name)
        a_tag.append(x_new_tag)

        if a_tag_name in ('th', 'td'):
            x_new_tag['data-eezz'] = 'template:cell'
            x_new_tag.string = '{cell.value}'
        elif a_tag_name == 'tr':
            x_new_tag['data-eezz'] = 'template:column'
        elif a_tag_name == 'tfoot':
            x_new_tag['data-eezz'] = 'template:navigation'
        return x_new_tag

    def compile_data(self, a_tag: Tag) -> None:
        x_data = a_tag['data-eezz']
        del a_tag['data-eezz']

        if a_tag.name in ('table'):
            a_tag['id'] = str(uuid.uuid1())[:8]
            a_tag['data-eezz-json'] = json.dumps({'name': 'directory'})
        if a_tag.name == 'th':
            a_json = {'event': {'call': 'table.do_sort', 'index': '{cell.index}'}, 'template': 'cell'}
            a_tag['onselect'] = 'eezz_click(event, self)'
            a_tag['data-eezz-json'] = json.dumps(a_json)
        if a_tag.name == 'td':
            a_json = {'template': 'cell'}
            a_tag['class'] = 'EezzClass_{cell.type}'
            a_tag['data-eezz-json'] = json.dumps(a_json)
        if a_tag.name == 'tr':
            if a_tag.parent.name == 'tbody':
                a_json = {'event': {'call': 'table.do_select', 'index': '{row.index}'}, 'template': 'row', 'match': 'body'}
            else:
                a_json = {'template': 'row', 'match': 'header'}
            a_tag['onselect'] = 'eezz_click(event, self)'
            a_tag['data-eezz-json'] = json.dumps(a_json)

    def generate_html_cells(self, a_tag: Tag, a_cell: TTableCell) -> Tag:
        """ The cell attributes distinguish between dictionary json-string and string values
        The json-string values are formatted in place using successive replace
        """
        x_fmt_attrs = {x_key: x_val.format(cell=a_cell) for x_key, x_val in a_tag.attrs.items() if
                       x_key != 'data-eezz-json'}
        if 'data-eezz-json' in a_tag.attrs:
            x_fmt_find = re.finditer(r'"[\w_]*({\w+[.\w]*})"', a_tag.attrs['data-eezz-json'])
            x_fmt_attrs['data-eezz-json'] = reduce(lambda x1, x2: x1.replace(x2[1], x2[1].format(cell=a_cell)), x_fmt_find, a_tag.attrs['data-eezz-json'])

        x_new_tag = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        x_new_tag.string = a_tag.string.format(cell=a_cell)
        return x_new_tag

    def generate_html_rows(self, a_html_cells: list, a_tag: Tag, a_row: TTableRow) -> Tag:
        """ This operation add fixed cells to the table.
        Cells which are not included as template for table data are used to add a constant info to the row"""
        x_fmt_attrs = {x_key: x_val.format(row=a_row)
                       for x_key, x_val in a_tag.attrs.items() if x_key != 'data-eezz-json'}
        if 'data-eezz-json' in a_tag.attrs:
            x_fmt_find = re.finditer(r'"[\w_]*({\w+[.\w]*})"', a_tag.attrs['data-eezz-json'])
            x_fmt_attrs['data-eezz-json'] = reduce(lambda x1, x2: x1.replace(x2[1], x2[1].format(row=a_row)), x_fmt_find, a_tag.attrs['data-eezz-json'])

        x_html_cells = [[copy.deepcopy(x)] if not x.has_attr('data-eezz-json') else a_html_cells for x in a_tag.css.select('th,td')]
        x_html_cells = list(chain.from_iterable(x_html_cells))
        x_new_tag = Tag(name=a_tag.name, attrs=x_fmt_attrs)
        for x in x_html_cells:
            x_new_tag.append(x)
        return x_new_tag

    def expand_table_segments(self, a_table_tag: Tag) -> Tag:
        x_template = Tag(name='template')
        x_row_template = a_table_tag.css.select('tr[data-eezz-json]')
        x_row_viewport = self.table_view.get_visible_rows()
        x_table_header = self.table_view.get_header_row()

        x_row_viewport.insert(0, x_table_header)

        # Evaluate the range and re-arrange
        x_range       = list(range(2).__reversed__())
        x_range_cells = [[x_row.cells[index] for index in x_range] for x_row in x_row_viewport]
        for x_row, x_cells in zip(x_row_viewport, x_range_cells):
            x_row.cells = x_cells

        # Evaluate match: It's possible to have a template for each row type
        # This allows us to format table header and body in the same stack
        x_format_row      = [([x_tag for x_tag in x_row_template if re.search(fr'"match"\s*:\s*"{x_row.type}"', x_tag.attrs['data-eezz-json'])], x_row)
                             for x_row in x_row_viewport]
        x_expand_cell     = [(list(product(x_tag[0].css.select('td,th'), x_row.cells)), x_tag[0], x_row)
                             for x_tag, x_row in x_format_row if x_tag]

        # Put all together and create HTML
        x_list_html_cells = [([self.generate_html_cells(x_tag, x_cell) for x_tag, x_cell in x_row_templates], x_tag_tr, x_row)
                             for x_row_templates, x_tag_tr, x_row in x_expand_cell]
        x_list_html_rows  = [(self.generate_html_rows(x_html_cells, x_tag_tr, x_row))
                             for x_html_cells, x_tag_tr, x_row in x_list_html_cells]

        x_temp_thead = Tag(name='thead')
        x_temp_tbody = Tag(name='tbody')
        x_temp_thead.append(x_list_html_rows[0])
        for x in x_list_html_rows[1:]:
            x_temp_tbody.append(x)
        x_template.append(x_temp_thead)
        x_template.append(x_temp_tbody)
        return x_template


if __name__ == '__main__':
    text1 = """
    <table data-eezz="
        name  : directory_list,
        table : TTable.test()
        column: [File, Size]
        ">
        <thead></thead>
        <tbody data-eezz="template">
            <tr></tr>
            <tr data-eezz="template: table.row
                events    : {
                    onselect : table.select_row( tr.row_id )
                }        
            ">
            <td data-eezz="
                css_class : eezz_string 
                template  : table.column, 
                attributes: {
                    id = column.id,
                }" >{column.value}</td>
            <td data-eezz="
                template  : column, 
                range     : [CResult],
                css_format: {
                    class : eezz_int_positive if column.value > 0 else eezz_int_negative
                }  
                attributes: {
                    id = column.id,
                }" >{column.value}</td>
            <td class="eezz_class_ico"><a href="{row.icon}"></a></td>
            <td class="eezz_class_ico">{row.icon}</td></tr>
    </tbody>
    </table>            
                """

    text2 = """
    <table data-eezz="name: directory, table: TDirView(path='/')"> </table>
    """

    aSoup = BeautifulSoup(text2, 'html.parser', multi_valued_attributes=None)
    list_table = aSoup.css.select('table[data-eezz]')

    x_gen = THttpAgent()
    x_table = x_gen.generate_html_table(list_table[0])
    print(x_table.prettify())
