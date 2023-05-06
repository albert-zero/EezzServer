import sys
import os
from   pathlib   import Path
from   datetime  import datetime, timezone
from   threading import Condition

sys.path.append('../eezz')
from table import TTable


class TDirView(TTable):
    """ Example class """

    def __init__(self, path: str, condition: Condition = None):
        # noinspection PyArgumentList
        super().__init__(column_names=['File', 'Size', 'Access Time'], title='Directory', condition=condition)

        a_path = Path(path)
        self.table_title = 'Directory'
        self.table_attrs = {'path': a_path}

        for x in a_path.iterdir():
            x_stat = os.stat(x)
            x_time = datetime.fromtimestamp(x_stat.st_atime, tz=timezone.utc)
            self.append([str(x.name), x_stat.st_size, x_time], attrs={'is_dir': x.is_dir()})


class TDirPng(TTable):
    def __init__(self, path: str, condition: Condition = None):
        # noinspection PyArgumentList
        super().__init__(column_names=['File', 'Size', 'Access Time'], title='DirPng', condition=condition)

        a_path = Path(path)
        self.table_title = 'Directory'
        self.table_attrs = {'path': a_path}

        for x in a_path.iterdir():
            x_stat = os.stat(x)
            x_time = datetime.fromtimestamp(x_stat.st_atime, tz=timezone.utc)
            self.append([str(x.name), x_stat.st_size, x_time], row_type='is_dir' if x.is_dir() else 'is_file')


if __name__ == '__main__':
    xdir = TDirView(path='/home/paul')
    xdir.print()

    xdir = TDirPng(path='/home/paul')
    xdir.print()
