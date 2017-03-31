'''
Created on 13.02.2017

@author: Paul
'''
import sqlite3
import os
import time
from   datetime import date
import datetime
from   eezz.table import TDbTable

class TDatabase:
    def __init__(self, aRootPath):
        self.mLocation = os.path.join(aRootPath, 'database', 'carfleet.db')
        if not os.path.exists(self.mLocation):            
            xDatabase = sqlite3.connect(self.mLocation)            
            xCursor   = xDatabase.cursor()
            xDatabase.execute('''CREATE TABLE tEvents
                 (cdate date, csymbol text, cdescr text)''')
            
            xDate = date(2017, 1, 14)
            for i in range(10):
                xDatabase.execute('''INSERT INTO tEvents (cdate, csymbol, cdescr) values(?,?,?) ''',
                    (xDate, chr(ord('A')+i), 'some description texts'))
                xDate += datetime.timedelta(weeks=4)
            xDatabase.commit()

if __name__ == '__main__':
    aDatabase = TDatabase('/Users/Paul/gitdev/eezzgit/EezzServer/webroot')
    
    xTDbTable = TDbTable(aDatabase.mLocation, {'select':['cdate','csymbol','cdescr'], 'from':['tEvents']})
    xTDbTable = xTDbTable.get_selected_obj()
    xTDbTable.printTable()
    print('passed')
    pass

