'''
Created on 13.02.2017

@author: Paul
'''
import sqlite3
import os
import time
from   datetime import date
import datetime
from   eezz.table    import TDbTable
from   eezz.service  import TBlackBoard
from   optparse      import OptionParser

class TChart(TDbTable):
    def __init__(self):        
        self.mBlackboard = TBlackBoard()
        self.mLocation   = os.path.join(self.mBlackboard.mRootPath, '..', 'database', 'carfleet.db') # os.path.join(aRootPath, 'database', 'carfleet.db')        
        
        if not os.path.exists(self.mLocation):            
            self.mDatabase = sqlite3.connect(self.mLocation) 
            self.mDatabase.execute('''CREATE TABLE tEvents
                 (cdate date, csymbol text, cdescr text)''')
            
            xDate = date(2017, 1, 14)
            for i in range(10):
                self.mDatabase.execute('''INSERT INTO tEvents (cdate, csymbol, cdescr) values(?,?,?) ''',
                    (xDate, chr(ord('A')+i), 'some description texts'))
                xDate += datetime.timedelta(weeks=4)
            self.mDatabase.commit()
        else:
            self.mDatabase   = sqlite3.connect(self.mLocation) 
        
        super().__init__(self.mLocation, {'select':['cdate','csymbol','cdescr'], 'from':['tEvents']})

    def get_selected_obj(self, index=-1, visible_items=None, visible_block=None, parameter=tuple()):
        xTable = super().get_selected_obj(index, visible_items, visible_block, parameter)
        return  {'return':{'code':200, 'value': xTable}}

if __name__ == '__main__':
    # Parse command line options
    aOptParser = OptionParser()
    aOptParser.add_option("-w", "--webroot",   dest="aWebRoot",    default="webroot",   help="Web-Root")
    
    (aOptions, aArgs) = aOptParser.parse_args() 
    xPath = os.path.join(aOptions.aWebRoot, 'public')
    
    aBlackBoard           = TBlackBoard()
    aBlackBoard.mDocRoot  = xPath
    aBlackBoard.mRootPath = xPath
    
    if os.path.isdir(xPath):
        os.chdir(xPath)
    else:
        print('webroot not found: {}'.format(xPath))
        os._exit(0)
    
    xChart = TChart()
    xTDBTable = xChart.get_selected_obj(-1)
    xTDBTable.printTable()
    print('passed')

