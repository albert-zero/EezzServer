#!/usr/bin/python3
#  # -*- coding: utf-8 -*-
"""
    Copyright (C) 2015  Albert Zedlitz

    TTraces
    Manages traces in database
    
"""
from   eezz.service  import TBlackBoard
from   eezz.table    import TTable, TDbTable
import sqlite3
import os, sys
import uuid
import traceback
import time
import datetime

# ------------------------------------------------------------------------------------
# Implement a trace interface for eezz components
# ------------------------------------------------------------------------------------
def singleton(aCls):
    """ Singleton pattern """
    aInstances = {}
    def getInstance():
        if aCls not in aInstances:
            aInstances[aCls] = aCls()
        return aInstances[aCls]
    return getInstance

@singleton
class TTracer:
    # ------------------------------------------------------------------------------------
    # Create database and insert the start event into the trace
    # ------------------------------------------------------------------------------------
    def __init__(self):
        self.mBlackboard = TBlackBoard()
        self.mLocation   = os.path.join(self.mBlackboard.mRootPath, 'database', 'traces.db')
        self.mCookie     = uuid.uuid1()
        self.mLevel      = 3
        self.mCount      = 100000
        self.mCid        = 0
        xExists          = os.path.isfile(self.mLocation)
        
        if not xExists:
            os.makedirs(os.path.join(self.mBlackboard.mRootPath, 'database'), exist_ok=True)
            
        xTraceDB = sqlite3.connect(self.mLocation)
        xCursor  = xTraceDB.cursor()
        
        if not xExists:
            # To convert timestamp use: datetime.datetime.fromtimestamp(1481201285)
            # xCursor.execute('create table TSession (CID integer PRIMARY KEY autoincrement, CStarttime timestamp, CArgs text)')
            xCursor.execute("""
                create table TTrace (
                    CID         integer PRIMARY KEY autoincrement,
                    CTraceTime  timestamp, 
                    CLevel      integer, 
                    CReason     text, 
                    CFileName   text, 
                    CFunction   text, 
                    CLine       integer, 
                    CAppErrNo   integer, 
                    CAppText    text)""")
        
        # Insert the start of the session as severity entry -1
        xFileName    = '/'.join( sys.argv[0].split(os.sep)[-3:] )
        xCursor.execute("""
                insert into TTrace (
                    CTraceTime, CLevel, CReason, CFileName, CFunction, CLine, CAppErrNo, CAppText) 
                    values (?, ?, ?, ?, ?, ?, ?, ?)""", 
                (time.time(), -1, 'Start', xFileName, 'main', '0', '0', '.'.join(sys.argv[1:])))
        
        self.mCid = xCursor.lastrowid
        
        # Prevent from overflow
        xCursor.execute("""
            delete from TTrace 
               where CTraceTime < (select CTraceTime from TTrace where CLevel = -1 order by CTraceTime DESC limit 1 offset 3)""") 
        
        # Table of sessions
        self.mSessionTable = TDbTable(self.mLocation, 
            {'select' :['CTraceTime as Start', 
                        """(select IFNULL( MIN(xtr.CTraceTime)-1, cast(STRFTIME("%s","now") as FLOAT) ) 
                            from   TTrace xtr  
                            where  xtr.CTraceTime > xtl.CTraceTime 
                            and    xtr.CLevel = -1 )""" + ' as End'], 
            'from'    :['TTrace xtl'], 
            'where'   : 'xtl.CLevel = -1'})

        # Table of traces
        self.mTracesTable = TDbTable(self.mLocation,
            {'select' :['CTraceTime as Time', 
                        'CLevel     as Level', 
                        'CReason    as Reason', 
                        'CFileName  as File',
                        'CFunction  as Function',
                        'CLine      as Line',
                        'CAppErrNo  as ErrorNo',
                        'CAppText   as Message'],
             'from'   :['TTrace'],
             'where'  : 'CTraceTime between ? and ?'}
            ) 
         
        xTraceDB.commit()
        xTraceDB.close()
        
    # ------------------------------------------------------------------------------------
    # Set the trace level. 
    # The higher the level the more output is generated
    # ------------------------------------------------------------------------------------
    def setTraceLevel(self, aLevel):
        self.mLevel = aLevel

    # ------------------------------------------------------------------------------------
    # Method to be used in case of exceptions
    # ------------------------------------------------------------------------------------
    def writeException(self, aLevel, aJsnReturn):
        if self.mLevel < aLevel or self.mCount <= 0:
            return

        self.mCount -= 1

        xType, xValue, xTraceback = sys.exc_info()
        xList        = traceback.extract_tb( xTraceback, linit=10 )
        xLine        = xList[0]
        xAppErr      = aJsnReturn['return']['code']
        xAppMsg      = aJsnReturn['return']['value']
        xFileName    = '/'.join( xLine[0].split(os.sep)[-3:] )
        xLineNo      = xLine[1]
        xFunction    = xLine[2]
        xStatement   = xLine[3]        
        xCombinedMsg = '{}:{}:{}'.format(xAppMsg, xStatement, xValue)

        xTraceDB     = sqlite3.connect(self.mLocation)
        xCursor      = xTraceDB.cursor()
        xCursor.execute("""
            insert into TTrace (CTraceTime, CLevel, CReason, CFileName, CFunction, CLine, CAppErrNo, CAppText) 
                values (?, ?, ?, ?, ?, ?, ?, ?)""", 
            (time.time(), aLevel, xType.__name__, xFileName, xFunction, xLineNo, xAppErr, xCombinedMsg))
        xTraceDB.commit()
        xTraceDB.close()
        
    # ------------------------------------------------------------------------------------
    # Method to be used for traces
    # ------------------------------------------------------------------------------------
    def write(self, aLevel, aReason, aJsnReturn = None, aMessage = ''):
        if self.mLevel < aLevel or self.mCount <= 0:
            return
        
        self.mCount -= 1
        xList        = traceback.extract_stack(limit=10) 
        xIndex       = len(xList) - 2
               
        xEntry       = xList[xIndex]
        xLineNo      = xEntry[1]
        xFunction    = xEntry[2]
        xFileName    = '/'.join( xEntry[0].split(os.sep)[-3:] )
        xAppErr      = 0
        xAppMsg      = ''

        if aJsnReturn and aJsnReturn.get('return'):
            xAppErr  = aJsnReturn['return']['code']
            xAppMsg  = aJsnReturn['return']['value']
        
        xCombinedMsg = ':'.join( [xAppMsg, aMessage] )
            
        xTraceDB     = sqlite3.connect(self.mLocation)
        xCursor      = xTraceDB.cursor()
        xCursor.execute("""
            insert into TTrace (CTraceTime, CLevel, CReason, CFileName, CFunction, CLine, CAppErrNo, CAppText) 
                values (?, ?, ?, ?, ?, ?, ?, ?)""", 
            (time.time(), aLevel, aReason, xFileName, xFunction, xLineNo, xAppErr, xCombinedMsg))
        xTraceDB.commit()
        xTraceDB.close()

    # ------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------
    def get_selected_sessions(self, index=-1, visible_items=None, visible_block=None, convert_time=False):
        self.mSessionTable.get_selected_obj(index, visible_items, visible_block)
        xTable = self.mSessionTable

        if convert_time:
            xCols   = xTable.get_columns()
            xOutput = TTable(aColNames = xCols[0][1:])
            for xRow in xTable:
                xOutput.append( [ str( datetime.datetime.fromtimestamp(xRow[1]) ), 
                                  str( datetime.datetime.fromtimestamp(xRow[2]) ) ] )
            return xOutput
        return xTable
    
    # ------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------
    def get_selected_traces(self, index=-1, visible_items=None, visible_block=None):
        xSessions = self.get_selected_sessions(index, visible_items, visible_block)
        xInx, xStart, xEnd = xSessions.get_selected_row(index)
        return self.mTracesTable.get_selected_obj(index, visible_items, visible_block, (xStart, xEnd))

    # ------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------
    def get_dictionary(self):
        return dict()

# ------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------
def globalfnct():
    try:
        print(xList['test'])
    except Exception as xEx:
        xTracer.writeException(1, {"return":{"code":600, "value":"error"}})
        # raise
    
# ------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    xList   = {}
    xBlackboard = TBlackBoard()
    xBlackboard.mRootPath = os.path.join('/', 'temp')
    xTracer = TTracer()
    
    for i in range(5):
        globalfnct()

    xSessions = xTracer.get_selected_sessions(convert_time=True)
    xSessions.printTable()
    
    xTraces   = xTracer.get_selected_traces(1)
    xTraces.printTable()
    
    pass
