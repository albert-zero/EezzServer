#!/usr/bin/python3
"""
  Copyright (C) 2015  Albert Zedlitz

  TTable is used for formatted ASCII output of a table structure. 
  It allows to access the table data for further processing e.g. for HTML output.
  It could also be used to access a SQL database table

  TTable is a list of TTableRow objects, each of which is a list of TCell objects.
  The TColumn holds the column names and is used to organize sort and filter.
  A TCell object could hold TTable objects for recursive tree structures.
"""

import os
import collections
from   dataclasses import dataclass
from   typing      import List, Dict, NewType, Tuple
from   enum        import Enum
from   pathlib     import Path
from   datetime    import datetime, timezone
from   threading   import Condition
from   copy        import deepcopy
import sqlite3


class TNavigation(Enum):
    """ Navigation control enum to navigate block steps in table """
    ABS  = 0
    NEXT = 1
    PREV = 2
    TOP  = 3
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
TTable = NewType('TTable', None)


@dataclass(kw_only=True)
class TTableRow:
    """ This structure is created for each row in a table
    It allows also to specify a sub-structure table """
    index:        int
    row_id:       str
    cells:        List[TTableCell]
    cells_filter: List[TTableCell] | None = None
    child:        TTable = None
    type:         str    = 'body'
    attrs:        dict   = None

    def __post_init__(self):
        if self.attrs:
            for x, y in self.attrs.items():
                setattr(self, x, y)


@dataclass(kw_only=True)
class TTable(collections.UserList):
    """ The table is derived from User-list to enable sort and list management """
    column_names:        List[str]
    column_names_map:    Dict[str, TTableCell] | None = None
    column_names_alias:  Dict[str, str]        | None = None
    column_names_filter: List[int]             | None = None

    virtual_table:  TTable      = None
    title:          str         = 'Table'
    attrs:          dict        = None
    visible_items:  int         = 20
    m_current_pos:  int         = 0
    m_column_descr: List[TTableColumn] = None
    selected_row:   TTableRow   = None
    header_row:     TTableRow   = None
    apply_filter:   bool        = False

    def __post_init__(self):
        """ Post init for a data class """
        super().__init__()
        self.m_column_descr   = [TTableColumn(index=x_inx, header=x_str, filter=x_str, width=len(x_str), sort=TSort.NONE) for x_inx, x_str in enumerate(self.column_names)]
        x_cells               = [TTableCell(value=x_str, index=x_inx, width=len(x_str)) for x_inx, x_str in enumerate(self.column_names)]
        self.header_row       = TTableRow(index=0, cells=x_cells, type='header')
        self.column_names_map = {x.value: x for x in x_cells}

    def filter_clear(self):
        self.apply_filter  = False

    def get_selected(self) -> TTableRow:
        return self.data[0]

    def filter_columns(self, column_names: List[Tuple[str, str]]) -> None:
        """ First tupel value is the column name at any position
        Second tupel value is the new column display name
        The filter is used to generate output. This function could also be used to reduce the number of
        visible columns """
        # Create a list of column index and a translation of the column header entry
        self.column_names_filter = list()
        self.column_names_alias  = {x: y for x, y in column_names}
        for x, y in column_names:
            x_inx = self.column_names_map[x].index
            self.column_names_filter.append(x_inx)
            self.m_column_descr[x_inx].filter = y
        self.apply_filter  = True

    def append(self, table_row: list, attrs: dict = None, row_type: str = 'body', row_id: str = '') -> None:
        """ Append a row into the table
        This procedure also defines the column type and the width """
        # define the type with the first line inserted
        x_inx       = len(self.data)
        x_row_descr = list(zip(table_row, self.m_column_descr))

        if row_id == '':
            row_id = str(x_inx)

        if x_inx == 0:
            for x_cell, x_descr in x_row_descr:
                x_descr.type = type(x_cell).__name__

        x_cells = [TTableCell(width=len(str(x_cell)), value=x_cell, index=x_descr.index, type=x_descr.type) for x_cell, x_descr in x_row_descr]
        x_row   = TTableRow(index=x_inx, cells=x_cells, attrs=attrs, type=row_type, row_id=row_id)
        super(collections.UserList, self).append(x_row)

        for x_cell, x_descr in x_row_descr:
            x_descr.width = max(len(str(x_cell)), x_descr.width)

    def get_header_row(self) -> TTableRow:
        """ Returns the header row. A filter for header values could be applied """
        if self.apply_filter:
            # Select the visible columns in the desired order and map the new names
            self.header_row.cells_filter = [deepcopy(self.header_row.cells[x]) for x in self.column_names_filter]
            for x in self.header_row.cells_filter:
                x.value = self.column_names_alias[x.value]
        return self.header_row

    def get_visible_rows(self, get_all=False) -> list:
        """ Return the visible rows """
        if len(self.data) == 0:
            return list()

        if get_all:
            x_start = 0
            x_end   = len(self.data)
        else:
            x_end   = min(len(self.data), self.m_current_pos + self.visible_items)
            x_start = max(0, x_end - self.visible_items)

        # Apply the filter for column layout
        for x_row in self.data[x_start: x_end]:
            if self.apply_filter:
                x_row.cells_filter = [x_row.cells[x] for x in self.column_names_filter]
            else:
                x_row.cells_filter = x_row
        return self.data[x_start: x_end]

    def get_child(self) -> TTableRow | None:
        """ Returns the child table, if exists, else None """
        if self.selected_row:
            return self.selected_row.child
        return None

    def do_select(self, row_id: str) -> TTableRow | None:
        for x_row in self.data:
            if x_row.row_id == row_id:
                self.selected_row = x_row
                return x_row
        return None

    def get_selected_row(self) -> TTableRow | None:
        if not self.data:
            return None
        if not self.selected_row:
            self.selected_row = self.data[0]
        return self.selected_row

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
        x_reverse = False

        # toggle sort direction
        self.m_column_descr[x_inx].sort = TSort.DESCENDING if x_reverse else TSort.ASCENDING
        super().sort(key=lambda x_row: x_row.cells[x_inx].value, reverse=x_reverse)

    def print(self) -> None:
        """ Print ASCII formatted table """
        x_format_type = {'int':      lambda x_size, x_val: ' {{:>{}}} '.format(x_size).format(x_val),
                         'str':      lambda x_size, x_val: ' {{:<{}}} '.format(x_size).format(x_val),
                         'float':    lambda x_size, x_val: ' {{:>{}.2}} '.format(x_size).format(x_val),
                         'datetime': lambda x_size, x_val: ' {{:>{}}} '.format(x_size).format(x_val.strftime("%m/%d/%Y, %H:%M:%S"))}

        x_column_descr = [self.m_column_descr[x] for x in self.column_names_filter] if self.apply_filter else self.m_column_descr

        print(f'Table : {self.title}')
        x_formatted_row = '|'.join([' {{:<{}}} '.format(x_col.width).format(x_col.filter) for x_col in x_column_descr])  if self.apply_filter else (
                          '|'.join([' {{:<{}}} '.format(x_col.width).format(x_col.header) for x_col in x_column_descr]))

        print(f'|{x_formatted_row}|')

        for x_row in self.data:
            x_cells        = [x_row.cells[x] for x in self.column_names_filter] if self.apply_filter else x_row.cells
            x_row_descr    = zip(x_cells, x_column_descr)
            x_format_descr = [(x_descr.type, x_descr.width, x_cell.value)
                              if  x_descr.type    in x_format_type else ('str', x_descr.width, str(x_cell.value))
                              for x_cell, x_descr in x_row_descr]

            x_formatted_row = '|'.join([x_format_type[x_type](x_width, x_value) for x_type, x_width, x_value in x_format_descr])
            print(f'|{x_formatted_row}|')


@dataclass(kw_only=True)
class TDbTable(TTable):
    """ Use TDBTable for optimized database access """
    offset:     int
    select_stm: dict
    path:       str
    size:       int

    def __post_init__(self):
        """ The TDBTable is assigned to a specific select statement """
        super().__init__()

    def __len__(self) -> int:
        """ Overwrite for function len to return the virtual size """
        return self.size

    def create_select_stm(self, options: dict | None, count_only: bool = True) -> str:
        """ Create a database statement for this object """
        x_select_stm = 'select count(*) as CCount ' if count_only else 'select '
        if options and options.get('select_options'):
            x_select_stm += options.get('select_options')
        x_select_stm += f' {self.select_stm["select"]} from {self.select_stm["from"]} '

        if self.select_stm.get('where'):
            x_select_stm += f' where {self.select_stm["where"]} '

        if count_only:
            return x_select_stm

        if self.select_stm.get('as'):
            x_select_stm += ' as ' + ' '.join(self.select_stm['as'])

        if options and options.get('group'):
            x_select_stm += ' group by ' + ' '.join(options["group"])

        if options and options.get('order'):
            x_select_stm += f' order by {options["order"]} '

        if options and options.get('asc_oe_desc'):
            x_select_stm += f' {options["asc_oe_desc"]} '

        x_select_stm += f' limit  {self.visible_items}'
        x_select_stm += f' offset {self.offset}'
        return x_select_stm

    def get_size(self):
        return self.size

    def sort(self, index: int = 1, sort_order: str = 'ASC') -> None:
        self.select(options={'order': self.column_names[index], 'asc_or_desc': sort_order})

    def navigate(self, where_togo: TNavigation = TNavigation.NEXT, position: int = 0) -> None:
        min_offset = 0
        max_offset = max(0, self.offset - self.visible_items)

        match where_togo:
            case TNavigation.NEXT:
                min_offset  = self.offset + self.visible_items
                self.offset = min(min_offset, max_offset)
            case TNavigation.PREV:
                max_offset  = self.offset - self.visible_items
                self.offset = max(min_offset, max_offset)
            case TNavigation.ABS:
                self.offset = min(max(0, position), max_offset)
            case TNavigation.TOP:
                self.offset = 0
            case TNavigation.LAST:
                self.offset = max_offset
        self.select(options=None)

    def select(self, options: dict | None) -> None:
        x_database = sqlite3.connect(self.path)
        x_cursor   = x_database.cursor()

        # Fetch the number of entries
        x_select   = self.create_select_stm(options=options, count_only=True)
        x_cursor.execute(x_select)
        self.size  = int(x_cursor.fetchone()[0])

        x_select   = self.create_select_stm(options=options)
        x_cursor.execute(x_select)
        x_result   = x_cursor.fetchall()

        # Evaluate the column names and the header row
        self.column_names = list()
        for x_col in x_cursor.description:
            self.column_names.append(x_col[0])
        self.m_column_descr = [TTableColumn(index=x_inx, header=x_str, width=len(x_str), sort=TSort.NONE) for x_inx, x_str in enumerate(self.column_names)]
        x_cells             = [TTableCell(value=x_str, index=x_inx, width=len(x_str)) for x_inx, x_str in enumerate(self.column_names)]
        self.header_row     = TTableRow(index=0, cells=x_cells, type='header')

        # Clear the data array and insert the selected view
        super().clear()
        for x_res in x_result:
            super().append([x_col for x_col in x_res])

        x_cursor.close()
        x_database.close()


if __name__ == '__main__':
    a_path  = Path.cwd()
    a_table = TTable(column_names=['File', 'Size', 'Access'])
    for xx in a_path.iterdir():
        x_stat = os.stat(xx.name)
        x_time = datetime.fromtimestamp(x_stat.st_atime, tz=timezone.utc)
        a_table.append([str(xx.name), x_stat.st_size, x_time], attrs={'path': xx})

    a_table.do_select(3)
    print(a_table.selected_row)

    a_table.navigate(TNavigation.NEXT)
    a_table.do_sort(1)
    a_table.print()

    a_table.filter_columns([('Size', 'Größe'), ('File', 'Datei')])
    a_table.print()
