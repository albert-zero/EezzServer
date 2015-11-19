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
import sqlite3
from   datetime import date
from   copy     import deepcopy
import uuid

# ---------------------------------------------------------------------------------
# TCell
# ---------------------------------------------------------------------------------
""" Defines a cell in a table column. This class contains type and ID information
"""
class TCell:
    def __init__(self, aValue='', aType=None, aObject=None, aStatus=None):
        self.mValue  = aValue
        self.mType   = aType
        self.mStatus = aStatus
        self.mObject = aObject

    def getObject(self):
        return self.mObject
    
    def getStatus(self):
        return self.mStatus
        
    def getType(self):
        try:
            return self.mObject.getType()
        except Exception:
            return self.mType

    def getValue(self):
        return self.mValue
                
    def __str__(self):
        return '{}'.format(self.mValue)
       
    
# ---------------------------------------------------------------------------------
# TTable
# ---------------------------------------------------------------------------------
class TTable(collections.UserList):    
    """ Defines a table, which could be used for formatted ASCI output or 
    table output in a UI
    """
    NAVIGATION_POS  = 0
    NAVIGATION_NEXT = 1
    NAVIGATION_PREV = 2
    NAVIGATION_TOP  = 3
    NAVIGATION_LAST = 4    
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def __init__(self, aColNames=list(), aHeaderStr='', aHeaderDic=dict(), visible_items=100):
        """ Initialize the TTable.
        The output is controlled by the mFormat description on the column type
        The width of each column is initialized to the size of the header
        """
        super().__init__()
        self.mSortReverse = False
        self.mToggleSort  = False
        self.mColsFmt     = list()
        self.mFormat      = {int   :'>{}', str : '{}', float : '>{}.2f', date  : '%A %d. %B %Y', TTable: '>{}', TCell: '>{}'}
        self.mColsName    = ['INX']
        self.mColsWidth   = None
        self.mColsType    = None
        self.mColsFilter  = None
        self.mHeaderDic   = dict()
        self.mHeaderStr   = aHeaderStr
        self.mCurrent     = 0
        self.mVisibleRows   = int(visible_items)
        self.mVisibleScroll = int(visible_items)
        self.mVisibleBlock  = int(visible_items)
        self.mRowInx      = 0
        self.mSelected    = 0
        self.mParent      = self
        self.mPath        = aHeaderStr
        self.mStartInx    = 1;
        self.mColsName.extend(aColNames)
        self.mSelChanged  = True

        
        self.mColsWidth   = [len(x) for x in self.mColsName]
        self.mColsType    = [str    for x in self.mColsName]
        self.mColsFilter  = ['*'    for x in self.mColsName]     
           
        self.mHeaderDic['table_caption'] = aHeaderStr
        self.mHeaderDic['table_prev']    = self.NAVIGATION_PREV 
        self.mHeaderDic['table_next']    = self.NAVIGATION_NEXT
        self.mHeaderDic['table_last']    = self.NAVIGATION_LAST
        self.mHeaderDic['table_top']     = self.NAVIGATION_TOP
        self.mHeaderDic['table_pos']     = self.NAVIGATION_POS
        self.mHeaderDic['table_size']    = 0
        self.mHeaderDic['table_current'] = 0
        self.mHeaderDic['table_nav_type']= 'default'
        self.mHeaderDic['table_path']    = aHeaderStr

        for xKey, xValue in aHeaderDic.items():
            self.mHeaderDic[xKey] = xValue
                    
        
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def __str__(self):
        """ Overloading the __str__ defines the output of the TTable object """
        return self.mHeaderStr.format(**self.mHeaderDic)

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_path(self):
        """ The TTable keeps track on the sub-TTable objects """
        return self.mPath
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_header(self):
        """ Return the dictionary """
        xRowElement = self.get_selected_row()
        
        self.mHeaderDic['table_size']     = len(self)
        self.mHeaderDic['table_position'] = self.mCurrent
        self.mHeaderDic['selected']       = xRowElement

        if xRowElement:
            for xInx, xName in enumerate(self.mColsName):
                if xRowElement[xInx] != None:
                    self.mHeaderDic['selected_' + xName] = str(xRowElement[xInx])
                else:
                    self.mHeaderDic['selected_' + xName] = ''                    
        else:
            for xInx, xName in enumerate(self.mColsName):
                self.mHeaderDic['selected_' + xName] = ''
            
        return self.mHeaderDic        

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def getId(self):
        if not self.mHeaderDic.get('table_id'):
            self.mHeaderDic['table_id'] = 'id{}'.format(uuid.uuid1().time_low)
        return self.mHeaderDic.get('table_id')
            
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_dictionary(self):
        """ Return the dictionary """
        return {'return':{'code':200, 'value': self.get_header()}}
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def setColumns(self, aColNames):
        """ set new columns for an empty set """
        if len(self.data) > 0: 
            return
        
        self.mColsName    = ['INX']
        self.mColsName.extend(aColNames)
        
        self.mColsWidth   = [len(x) for x in self.mColsName]
        self.mColsType    = [str    for x in self.mColsName]
        self.mColsFilter  = ['*'    for x in self.mColsName]        
       
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_columns(self):
        """ Return the column names """
        return [self.mColsName]

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_columns_type(self):
        """ Return the column types """
        return self.mColsType

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def set_columns_type(self, aColsType):
        """ Set column types """
        self.mColsType = aColsType

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def setColFmt(self, aType, aFmt):
        """ Set column output format for the specified type """
        self.mFormat.update(aType, aFmt)

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def getColFmt(self, aType, aFmt):
        """ Return column output format for the specified type """
        return self.mFormat

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def clear(self):
        """ Reset table and internal state """
        self.mSelChanged = True
        self.mRowInx   = 0
        self.mSelected = 0
        self.mCurrent  = 0
        super().clear()
        
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def append(self, aRow=list(), aCell=None, aRowInx=None):
        """ Add values to the table """
        xRow = None
        
        if len(aRow) != len(self.mColsName)-1:
            return
        
        if aRowInx != None:
            self.mRowInx = int(aRowInx)
        
        if aCell:
            aCell.mValue = self.mRowInx
            xRow = [aCell] + aRow
        else:
            xRow = [self.mRowInx] + aRow

        if aRowInx == None:
            self.mRowInx += 1

        
        for xElem in xRow:
            if isinstance(xElem, TTable):
                xPath   = '{}/{}'.format(self.mPath, xElem.mPath)
                if xPath.startswith('//'):
                    xElem.mPath = xPath[1:]
                else:
                    xElem.mPath = xPath
                xElem.mHeaderDic['table_path'] = xPath
                xElem.mParent = self 
        
        if len(self.data) == 0:
            self.mColsType = [type(x) for x in xRow]                
        
        super(collections.UserList, self).append(xRow)
        self.set_visible_items(self.mVisibleScroll, self.mVisibleBlock)
        
        aColsWidth      = [len(str(x)) for x in xRow]
        self.mColsWidth = [max(x)      for x in zip(aColsWidth, self.mColsWidth)] 
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_parent(self):
        """ Parent in a tree of hierarchical organized tables """
        return self.mParent 
        
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def setHeader(self, aHeaderDict):
        """ Add new values to the header dictionary """
        self.mHeaderDict.update(aHeaderDict)
            
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def do_sort(self, index=0):
        """ Toggle sort on a given column index
        """
        aInx    = min(max(0, int(index)), len(self.mColsName)-1)
        aResult = list()
        self.mSortReverse =  not self.mSortReverse
        
        if self.mColsType[aInx] == int:
            aResult = sorted(self, key=lambda xRow: int(xRow[aInx]),   reverse=self.mSortReverse)
        elif self.mColsType[aInx] == float:
            aResult = sorted(self, key=lambda xRow: float(xRow[aInx]), reverse=self.mSortReverse)
        else:
            aResult = sorted(self, key=lambda xRow: str(xRow[aInx]),   reverse=self.mSortReverse)
        self.data = aResult

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_selected_obj(self, index = -1, visible_items = None, visible_block = None):
        """ Drill down in a table hierarchy 
        """
        aInx   = int(index)
        xTable = self 
        
        if len(self) == 0:
            return self
        
        xRowElement = self.get_selected_row(aInx)        
        if xRowElement and isinstance(xRowElement[1], TTable):
            xTable = xRowElement[1]
        
        xTable.set_visible_items(visible_items, visible_block)
        return xTable

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_selected_row(self, index = -1):
        """ Return the row for a given row-id
        """
        xSaveInx = int(index)
        if xSaveInx == -1:
            xSaveInx = self.mSelected
        
        for xInx, xElem in enumerate(self):
            if int(str(xElem[0])) == xSaveInx:  
                self.mSelected = xSaveInx
                self.mHeaderDic['selected'] = xElem
                return xElem 
        
        if self.data:
            return self.data[0]       

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def do_select(self, index = -1):
        """ Find the row for a given row id 
        """
        xSaveInx = int(index)
        if xSaveInx == -1:
            xSaveInx = self.mSelected
        else:
            #-- print('tbale select')
            self.mSelChanged = (xSaveInx != self.mSelected)
            
        for xInx, xElem in enumerate(self):
            if int(str(xElem[0])) == xSaveInx:  
                self.mSelected = xSaveInx
                self.mHeaderDic['selected'] = xElem

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def hasChanged(self):
        xChanged         = self.mSelChanged
        self.mSelChanged = False
        return xChanged
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_selected_index(self, index = -1):        
        """ Return the index for a given row-id or -1 if not found
        """
        if index == -1:
            index = self.mSelected

        for xInx, xElem in enumerate(self):
            if int(str(xElem[0])) == index:  
                return xInx
        return -1
                
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def printTable(self):
        """ Print ACII formatted table 
        """
        xFmtRow = list()
        for xType, xWidth in zip(self.mColsType, self.mColsWidth):
            if xType in self.mFormat:
                xFmtRow.append(self.mFormat[xType].format(xWidth))
            else:
                xFmtRow.append('{}'.format(xWidth))
        
        if len(self.mHeaderStr) > 0: 
            print('Table = {}'.format( self.mHeaderStr.format(**self.mHeaderDic)))
            
        xLine = [format(xVal, str(xWidth)) for xVal, xWidth in zip(self.mColsName, self.mColsWidth)]
        print('|-{}-|'.format(' |'.join(xLine)))
    
        if len(self) == 0:
            return
            
        xEndInx = min(len(self.data), self.mCurrent + self.mVisibleRows)
        xBegInx = max(0, xEndInx - self.mVisibleRows)
        
        for xRow in self.data[xBegInx:xEndInx]:
            xLine = [format(xVal, xFmt) for xVal, xFmt in zip(xRow, xFmtRow)]
            print('| {} |'.format(' |'.join(xLine)))
    
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def set_visible_items(self, visible_items, visible_block):
        """ Switch between block and scroll
        """        
        if visible_items:            
            self.mVisibleScroll = max(8, int(visible_items))
        if visible_block:            
            self.mVisibleBlock  = max(8, int(visible_block))
        
        if len(self) > self.mVisibleScroll:
            self.mHeaderDic['table_nav_type'] = 'block'
            self.mVisibleRows = self.mVisibleBlock
        else:
            self.mHeaderDic['table_nav_type'] = 'default'
            self.mVisibleRows = self.mVisibleScroll

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def do_navigate(self, where = NAVIGATION_NEXT, pos = 0):
        """ Navigate in block mode
        """
        self.mSelected   = 0
        self.mSelChanged = True

        aInx = int(where)

        if aInx   == TTable.NAVIGATION_POS:
            self.mCurrent = max(0, min(int(pos), len(self) - self.mVisibleRows))
        elif aInx == TTable.NAVIGATION_NEXT:
            self.mCurrent = max(0, min(len(self) - self.mVisibleRows, self.mCurrent + self.mVisibleRows))
        elif aInx == TTable.NAVIGATION_PREV:
            self.mCurrent = max(0, self.mCurrent - self.mVisibleRows)
        elif aInx == TTable.NAVIGATION_TOP:
            self.mCurrent = 0
        elif aInx == TTable.NAVIGATION_LAST:
            self.mCurrent = max(0, len(self) - self.mVisibleRows)
        
        self.mHeaderDic['table_current'] = self.mCurrent 

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_raw_rows(self):
        """ Return table rows 
        """
        if len(self) == 0:
            return list()
        
        xEndInx = min(len(self.data), self.mCurrent + self.mVisibleRows)
        xBegInx = max(0, xEndInx - self.mVisibleRows)
        return self.data[xBegInx:xEndInx]
        
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_rows(self):
        """ Return formatted rows 
        """
        if len(self) == 0:
            return list()

        xFmtRow = [ self.mFormat[xType].format(xWidth)  for xType, xWidth in zip(self.mColsType, self.mColsWidth)]
        aLines  = list()

        xEndInx = min(len(self.data), self.mCurrent + self.mVisibleRows)
        xBegInx = max(0, xEndInx - self.mVisibleRows)
                
        for xRow in self.data[xBegInx:xEndInx]:
            aLines.append( [format(xVal, xFmt) for xVal, xFmt in zip(xRow, xFmtRow)] )
        return aLines
    
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
""" The TDBTable defines an optimized database access """
class TDbTable(TTable):
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def __init__(self, database, select):        
        self.mOffset      = 0
        self.mDatabase    = database
        self.mSelectParam = None
        self.mSortCol     = None
        self.mSelectObj   = select
        self.mSelectCmd   = dict()
        self.mVirtualSize = 0
        self.mExecute     = True
        
        # Create a select statement to evaluate the context
        self.mSelectCmd   = deepcopy(select)
        
        xColumnList = self.mSelectCmd['select']
        super().__init__(aColNames = xColumnList)

        #xColumnList.insert(0, 'count(*) as CCount')
        #self.mSelectCmd['select'] = xColumnList

        #super().__init__(aColNames=xColumnList)

        #xSelectStmt       = self.getSelectStmt(self.mSelectCmd, self.mSelectParam)
        #xDatabase         = sqlite3.connect(self.mDatabase)
        #xCursor           = xDatabase.cursor()
        #xCursor.execute(xSelectStmt)
        
        #self.mRowInx      = int(xCursor.fetchone()[0])
        #self.mVirtualSize = self.mRowInx
        #xColNames         = list()
        
        #for xCol in xCursor.description:
        #    xColNames.append(xCol[0])

        # Store column names except CCount
        #self.setColumns(xColNames[1:])
        #xCursor.close()
        #xDatabase.close()
        
        #self.mSelectCmd   = deepcopy(select)

    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def __len__(self):
        """ Overwrite for function len to return the virtual size
        """
        return int(self.mVirtualSize)
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def do_navigate(self, where = TTable.NAVIGATION_NEXT, pos = 0):
        """ Overwrite navigation to decide for new database access
        """
        self.mCurrent = self.mOffset
        super().do_navigate(where, pos)
        self.mOffset  = self.mCurrent
        self.mCurrent = 0
        self.mExecute = True            
                  
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def getSelectStmt(self, aSelectCmd):
        """ Create a database statement for this object
        """
        xSelectStmt = 'select '
        
        if aSelectCmd.get('select') == None or aSelectCmd.get('from') == None:
            raise Exception('select statement required')
        
        if aSelectCmd.get('distinct') != None:
            xSelectStmt += ' distinct'

        xSelectStmt += ','.join(aSelectCmd['select'])
        xSelectStmt += ' from '
        xSelectStmt += ','.join(aSelectCmd['from'])
        
        if aSelectCmd.get('where')  != None:
            xSelectStmt += ' where ' + aSelectCmd['where']

        if aSelectCmd.get('equal')  != None:
            xSelectStmt += ' where '
            for xCol, xVal in aSelectCmd['equal'].items():
                xSelectStmt += ' ' + xCol + '=' + xVal 

        if aSelectCmd.get('group')  != None:
            xSelectStmt += ' group by ' + aSelectCmd['group']

        if aSelectCmd.get('order')  != None:
            xSelectStmt += ' order by ' + aSelectCmd['order']
 
            if aSelectCmd.get('sort') != None:
                xSelectStmt += '  ' + aSelectCmd.get('sort')

        if aSelectCmd.get('limit')  != None:
            xSelectStmt += ' limit ' + aSelectCmd['limit']

        if aSelectCmd.get('offset') != None:
            xSelectStmt += ' offset ' + aSelectCmd['offset']
 
        return xSelectStmt
        
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def get_selected_obj(self, index = -1, visible_items = None, visible_block = None, parameter = tuple()):
        """ Access the database and fill table with data slice
        """
        aInx       = int(index)
        xParameter = parameter
        
        self.do_select(aInx)
        self.set_visible_items(visible_items, visible_block)

        if not self.mExecute:
            if self.mSelectParam == parameter:
                return self
        self.mSelectParam = parameter
        
        xDatabase   = sqlite3.connect(self.mDatabase)
        xCursor     = xDatabase.cursor()
        
        xSelectCmd  = deepcopy(self.mSelectCmd)
        xSelectCmd['select'] = ['count(*) as CCount']
        xSelectStmt = self.getSelectStmt(xSelectCmd)
        
        xCursor.execute(xSelectStmt, xParameter)            
        self.mVirtualSize = xCursor.fetchone()[0]

        
        xSelectCmd  = deepcopy(self.mSelectCmd)
        xSelectCmd['limit']  = str(self.mVisibleRows)
        xSelectCmd['offset'] = str(self.mOffset)
        xSelectStmt = self.getSelectStmt(xSelectCmd)

        xCursor.execute(xSelectStmt, xParameter)
        xResultSet     = xCursor.fetchall()
        super().clear()
        
        xColNames = list()
        for xCol in xCursor.description:
            xColNames.append(xCol[0])
        self.setColumns(xColNames)
        
        self.mRowInx   = self.mOffset
        self.mSelected = 0
        self.mCurrent  = 0        
        xNumRows       = len(xResultSet)
        
        for xInx, xResult in enumerate(xResultSet):
            if self.mSortReverse:
                xRowInx = self.mOffset + xNumRows - xInx - 1
            else:
                xRowInx = self.mOffset + xInx
            self.append(list(xResult), aRowInx = xRowInx)
            
        xCursor.close()
        xDatabase.close()
        
        self.mSelChanged = True
        self.mExecute    = False
        return self
    
    # ---------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------
    def do_sort(self, index=1):
        """ Create a sort for a given column index on database
        """
        aInx = min(max(1, int(index)), len(self.mColsName)-1)
        self.mSortCol     = aInx
        self.mSortReverse =  not self.mSortReverse

        self.mSelectCmd['order'] = self.mColsName[aInx]
        if self.mSortReverse:
            self.mSelectCmd['sort'] = 'DESC'
        else:
            self.mSelectCmd['sort'] = 'ASC'
        
        self.mExecute  = True
        self.mOffset   = 0
        self.mCurrent  = 0
        self.mSelected = 0
                    
        # self.get_selected_obj()    

# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
class TTrace(TTable):
    def __init__(self):
        self.mTraceTable = TTable(['code', 'values'])
    
    def append(self, code, values):
        self.mTraceTable.append(code, values)
        pass
    
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
if __name__ == '__main__':
    xDbPath = 'eezz.db'
    aTable  = TDbTable(xDbPath, {'select':['CTitle', 'CStatus'], 'from':['TDocuments']})
    aTable.do_sort(1)
    aTable  = aTable.get_selected_obj()
    aTable.printTable()
    
    
    

