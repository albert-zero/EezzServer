#!/usr/bin/python3
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

 
Documentation:
  TTable is used for formatted ASCII output of a table structure. 
  It allows to accessing the table data for further processing e.g. for HTML output. 
  It could also be used to access a SQL database table
  
  Each table cell might contain a TTable or TCell object, which could be used to store 
  information about recursive structures, type information or unique IDs for any entry.
  
  Each table has an index allowing unique selection after sorting. This is always the first column
  For HTML output and it's possible (and recommended) to hide this column.     
"""
import os
import collections
import typing
from   dataclasses import dataclass
from   typing      import List, Callable
from   enum        import Enum
from   pathlib     import Path
from   datetime    import datetime, timezone
from   threading   import Condition


class TNavigation(Enum):
    """ Navigation control enum to navigate block steps in table """
    ABS =  0
    NEXT = 1
    PREV = 2
    TOP =  3
    LAST = 4


class TSort(Enum):
    """ Sorting control enum to define sort on columns """
    NONE       = 0
    ASCENDING  = 1
    DESCENDING = 2


@dataclass(kw_only=True)
class TTableCell:
    """ Table cell is the smallest unit of a table """
    width:  int
    value:  int | float | str | datetime
    index:  int  = 0
    type:   str  = 'str'
    attrs:  dict = None


@dataclass(kw_only=True)
class TTableColumn:
    """ Summarize the cell properties in a column
    which includes sorting and formatting """
    index:  int
    header: str
    width:  int   = 10
    filter: str   = ''
    sort:   TSort = TSort.NONE
    type:   str = ''
    attrs:  dict = None


# forward declaration
TTable = typing.NewType('TTable', None)


@dataclass(kw_only=True)
class TTableRow:
    """ This structure is created for each row in a table
    It allows also to specify a sub-structure table """
    index:  int
    cells:  List[TTableCell]
    child:  TTable = None
    type:   str    = 'body'
    attrs:  dict   = None

    def __post_init__(self):
        if self.attrs:
            for x, y in self.attrs.items():
                setattr(self, x, y)


@dataclass(kw_only=True)
class TTable( collections.UserList ):
    """ The table is derived from Userlist to enable sort and list management """
    column_names:  List[str]
    title:          str         = 'Table'
    attrs:          dict        = None
    condition:      Condition   = None
    visible_items:  int         = 20
    m_current_pos:  int         = 0
    m_column_descr: List[TTableColumn] = None
    selected_row:   TTableRow   = None
    header_row:     TTableRow   = None

    def __post_init__(self):
        """ Post init for a data class """
        super().__init__()
        self.m_column_descr = [TTableColumn(index=x_inx, header=x_str, width=len(x_str), sort=TSort.NONE) for x_inx, x_str in enumerate(self.column_names)]
        x_cells             = [TTableCell(value=x_str, index=x_inx, width=len(x_str)) for x_inx, x_str in enumerate(self.column_names)]
        self.header_row     = TTableRow(index=0, cells=x_cells, type='header')

    def append(self, table_row: list, attrs: dict = None, row_type: str = 'body') -> None:
        """ Append a row into the table
        This procedure also defines the column type and the width """
        # define the type with the first line inserted
        x_inx       = len(self.data)
        x_row_descr = list(zip(table_row, self.m_column_descr))

        if x_inx == 0:
            for x_cell, x_descr in x_row_descr:
                x_descr.type = type(x_cell).__name__

        x_cells = [TTableCell(width=len(str(x_cell)), value=x_cell, index=x_descr.index, type=x_descr.type) for x_cell, x_descr in x_row_descr]
        x_row   = TTableRow(index=x_inx, cells=x_cells, attrs=attrs, type=row_type)
        super(collections.UserList, self).append(x_row)

        for x_cell, x_descr in x_row_descr:
            x_descr.width = max(len(str(x_cell)), x_descr.width)

    def get_header_row(self) -> TTableRow:
        return self.header_row

    def get_visible_rows(self) -> list:
        """ Return the visible rows """
        if len(self.data) == 0:
            return list()

        x_end   = min(len(self.data), self.m_current_pos + self.visible_items)
        x_start = max(0, x_end - self.visible_items)
        return self.data[x_start : x_end]

    def get_child(self) -> TTableRow | None:
        """ Returns the child table, if exists, else None """
        if self.selected_row:
            return self.selected_row.child
        return None

    def do_select(self, index: int) -> TTableRow | None:
        for x_row in self.data:
            if x_row.index == index:
                self.selected_row = x_row
                return x_row
        return None

    def navigate(self, where_togo: TNavigation = TNavigation.NEXT, position: int = 0) -> None:
        """ Navigate in block mode """
        match where_togo:
            case TNavigation.NEXT:
                self.m_current_pos = max(0, min(len(self.data) - self.visible_items, self.m_current_pos + self.visible_items))
            case TNavigation.PREV:
                self.m_current_pos = max(0, self.m_current_pos - self.visible_items)
            case TNavigation.ABS:
                self.m_current_pos = max(0, min(int(position), len(self) - self.visible_items))
            case TNavigation.TOP:
                self.m_current_pos = 0
            case TNavigation.LAST:
                self.m_current_pos = max(0, len(self) - self.visible_items)

    def do_sort(self, column_inx: int) -> None:
        """ Toggle sort on a given column index"""
        x_inx     = min(max(0, int(column_inx)), len(self.column_names) - 1)
        x_reverse = self.m_column_descr[x_inx].sort == TSort.DESCENDING

        # toggle sort direction
        if x_reverse:
            self.m_column_descr[x_inx].sort = TSort.ASCENDING
        else:
            self.m_column_descr[x_inx].sort = TSort.DESCENDING
        super().sort(key=lambda x_row: x_row.cells[x_inx].value, reverse=x_reverse)

    def print(self) -> None:
        """ Print ASCII formatted table """
        x_format_type = {'int':      lambda x_size, x_val: ' {{:>{}}} '.format(x_size).format(x_val),
                         'str':      lambda x_size, x_val: ' {{:<{}}} '.format(x_size).format(x_val),
                         'float':    lambda x_size, x_val: ' {{:>{}.2}} '.format(x_size).format(x_val),
                         'datetime': lambda x_size, x_val: ' {{:>{}}} '.format(x_size).format(x_val.strftime("%m/%d/%Y, %H:%M:%S"))}

        print(f'Table : {self.title}')
        x_formatted_row = '|'.join( [' {{:<{}}} '.format(x_col.width).format(x_col.header) for x_col in self.m_column_descr ])
        print(f'|{x_formatted_row}|')

        for x_row in self.data:
            x_row_descr     = zip(x_row.cells, self.m_column_descr)
            x_format_descr  = [(x_descr.type, x_descr.width, x_cell.value)
                               if x_descr.type in x_format_type else ('str', x_descr.width, str(x_cell.value))
                               for x_cell, x_descr in x_row_descr]

            x_formatted_row = '|'.join([x_format_type[x_type](x_width, x_value) for x_type, x_width, x_value in x_format_descr])
            print(f'|{x_formatted_row}|')


if __name__ == '__main__':
    a_path  = Path.cwd()
    a_table = TTable(column_names=['File', 'Size', 'Access'])
    for xx in a_path.iterdir():
        x_stat = os.stat(xx.name)
        x_time = datetime.fromtimestamp(x_stat.st_atime, tz=timezone.utc)
        a_table.append([str(xx.name), x_stat.st_size, x_time], attrs={'path': xx})

    a_table.do_select(3)
    print(a_table.selected_row.path)

    a_table.navigate(TNavigation.NEXT)
    a_table.do_sort(1)
    a_table.print()
