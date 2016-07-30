# -*- coding: utf-8 -*-
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

 
"""
import os, re, io, sys
import uuid
import html
from   html.parser   import HTMLParser
import importlib
import urllib
import gettext
from   collections    import deque
import json
import threading

from   eezz.table          import TTable, TCell
from   eezz.service        import TBlackBoard


# --------------------------------------------------------
#  Administration of an HTML tag
#  --------------------------------------------------------
class THtmlTag(dict):    
    # --------------------------------------------------------
    # Initialize
    # --------------------------------------------------------
    def __init__(self, aTagName):
        super().__init__()
        
        self.mTagName    = aTagName
        self.mValue      = None
        self.mColumnInx  = None
        self.mObject     = None
        self.mInnerHtml  = io.StringIO()
        self.mDictionary = dict()
        self.mValueList  = list()
        self.mParent     = None
        self.mJsonObj    = None
        
        self.mReturn     = dict()
        self.mTemplate   = dict()
        self.mChildren   = list()
        self.mElements   = list()
        self.mId         = str()
  
    # --------------------------------------------------------
    # Generate HTML output according the parser input 
    # --------------------------------------------------------
    def generateHtml(self, aValues = None, language = None): 
        with io.StringIO() as xOuterHtml:
            xOuterHtml.write('<{}'.format(self.mTagName))
            
            for xKey, xValue in self.items():
                if not xKey in ['data-eezz-template', 'return']: 
                    xOuterHtml.write(' {}=\"{}\"'.format(xKey, xValue))                    
                
            if 'data-eezz-event' in self.keys():
                if self.mTagName == 'select':
                    xOuterHtml.write(' onchange="easyClick(event, this)"')
                elif self.mTagName == 'input' and self.get('type') == 'file':
                    xOuterHtml.write(' onchange="easyClick(event, this)"')
                elif self.mTagName == 'input' and self.get('type') == 'range':
                    xOuterHtml.write(' onchange="easyClick(event, this)"')
                else:
                    xOuterHtml.write(' onclick="easyClick(event, this)"')
          
            xOuterHtml.write('>')
            xInnerHtm = self.mInnerHtml.getvalue()
            
            try:
                if aValues == None:
                    xOuterHtml.write( xInnerHtm )
                elif isinstance(aValues, dict):
                    xOuterHtml.write( xInnerHtm.format(**aValues) )
                elif isinstance(aValues, list):
                    xOuterHtml.write( xInnerHtm.format(*aValues) )
                else:
                    xOuterHtml.write( xInnerHtm.format(aValues) )
            except IndexError as xEx:
                pass
            
            xOuterHtml.write('</{}>'.format(self.mTagName))  
            return xOuterHtml.getvalue()

   
# --------------------------------------------------------
# TEezzAgent takes a HTML file as input and modifies
# tag attributes and data content
# --------------------------------------------------------
class TEezzAgent(HTMLParser):
    
    # --------------------------------------------------------
    # Initialize the parser
    # --------------------------------------------------------
    def __init__(self, doc_root=None, client_address=None, aWebClient=None):        
        self.mWebClient  = aWebClient
        self.mSession    = True
        self.mTagStack   = deque()
        self.mFileListener = dict()
        self.mElements   = dict()
        self.mCltAddr    = client_address
        self.mCurrDomain = 'index'
        self.mCurrentDocument = None
        self.mLanguage    = None
        self.mFileHeader  = None
        self.mUpdateBody  = str()
        self.mDatabase    = THtmlTag('table')
        self.mTraceStack  = TTable()
        self.mArguments   = None
        self.mThreads     = list()
        self.mRunning     = True
        self.mtimer       = 0
        self.mGlobals     = dict()
        self.mUpdateVector = dict()
        self.mCookie      = uuid.uuid1()
        self.mBlackboard  = TBlackBoard()
        self.mAsyncThr    = None
        self.mEvent       = threading.Event()
        
        self.mEvent.clear()
        if doc_root:
            self.mBlackboard.mDocRoot = doc_root
            
        #if not TEezzAgent.mGlobals:
        #    TEezzAgent.mGlobals['__buildins__'] = dict()
        
        self.mGlobals ['eezzAgent'] = self
        
        #if not TEezzAgent.mGlobals.get('TServiceAdmin'):
        #    TEezzAgent.mGlobals['TServiceAdmin'] = TServiceAdmin 
            
        self.mElements['eezzAgent'] = THtmlTag('script')
        self.mElements['eezzAgent'].mObject = self 
        
        self.mLock      = threading.Lock()
        self.mLockTrace = threading.Lock()
        self.mWebSocket = threading.Lock()
        
        self.mRoot = THtmlTag('document')
        self.mTagStack.append( self.mRoot ) 
        self.mState      = None
        self.startServices()
        
        super().__init__()

    # --------------------------------------------------------
    # --------------------------------------------------------
    def startServices(self):
        pass
        
    # --------------------------------------------------------
    # Handle file downloads
    # --------------------------------------------------------
    def handle_download(self, aJsonObj, aStream):
        try:
            aJsonObj['return'] = {'code':200, 'value':'OK'}
            
            xCallPath = aJsonObj['reader'].split('.') 
            xClassName, xMethodName = xCallPath
            xMethod   = getattr(self.mGlobals.get(xClassName), xMethodName)
            xJsonResp = xMethod(aJsonObj, aStream)  
                  
            try:
                if isinstance(xJsonResp, dict):
                    aJsonObj['return'] = xJsonResp.get('return')
                    xCode  = xJsonResp['return']['code']
                    xValue = xJsonResp['return']['value']
                    xArgs  = xJsonResp['return'].get('args')
                    
                    if xJsonResp['return'].get('progress'):
                        xValue = xJsonResp['return']['progress']
                        aJsonObj['update'] = dict()
                        
                        for xKey in aJsonObj.get('progress'):
                            aJsonObj['update'][xKey] = "{}%".format(xValue)
                                        
                    if xCode != 101 and xCode != 200: 
                        if isinstance(xValue, TCell):
                            self.mTraceStack.append(aCell=xValue)
                        else:
                            xList = [ xValue ]
                            if isinstance(xArgs, list):
                                xList += xArgs
                            self.mTraceStack.append(aCell=TCell(aType=xCode, aObject=xList))
            except KeyError:
                self.mTraceStack.append(aCell=TCell(aType=xCode, aObject=[xValue]))
            except AttributeError:
                pass

        except AttributeError as xEx:
            self.mTraceStack.append(aCell=TCell( aType=409, aObject=[xCallPath]))
        
        xTraceUpdate = dict()
        with self.mLock:
            xDatabase = self.evalTraceReturn(aJsonObj)
            if xDatabase:
                xTraceUpdate['update'] = {xDatabase.get('name') + '.innerHTML':'*'}
            
        xUpdateQuotes = dict()    
        if aJsonObj.get('update'):
            aJsonObj.update(xTraceUpdate)
            for xKey, xValue in aJsonObj['update'].items(): 
                xUpdateQuotes[xKey] = urllib.parse.quote(xValue.encode('utf-8'))
            aJsonObj['update'] = xUpdateQuotes
        return aJsonObj

    # --------------------------------------------------------
    # --------------------------------------------------------
    def jsonCallback(self, aJson):        
        xCallPath = None
        xCallPar  = dict()
        xResponse = None
        xRetList  = list()
        xRetCode  = 100
        xObject   = None
        
        if not aJson.get('callback'):
            return
        
        try:                
            for xListKey, xListVal in aJson['callback'].items():                
                xCallPath = xListKey

                if isinstance(xListVal, dict):
                    xCallPar = xListVal
                
                xClassName, xMethodName = xCallPath.split('.') 
                if self.mGlobals.get(xClassName) == None:
                    self.mTraceStack.append(aCell=TCell(aType=408, aObject=[xCallPath]))
                    continue
                
                xMethod   = getattr(self.mGlobals.get(xClassName), xMethodName)
                xResponse = xMethod(**xCallPar)
                
                if not isinstance(xResponse, dict):
                    xRetList.append( {'code':100, 'value':'OK'} )
                    continue
                xRetList.append( xResponse['return'] )
            
            for xEntry in xRetList:
                xCode    = xEntry['code']
                xRetCode = max(xRetCode, xCode)

                if xCode not in (100, 105, 200, 201):
                    xList  = [ str( xEntry['value'] ) ]
                    if isinstance(xEntry.get('args'), list):
                        xList += xEntry.get('args')
                    self.mTraceStack.append(aCell=TCell(aType=xCode, aObject=xList))
                    continue
                if not isinstance(xEntry['value'], str):
                    xObject = xEntry['value']
            
            try:
                if aJson.get('name'):
                    aJson['return']      = {'code': xRetCode, 'value':''}        
                    xName                = aJson.get('name')
                    xHtmlTag             = self.mElements[ xName ]
                    xResponse            = xObject.get_dictionary()
                    xHtmlTag             = self.mElements[ xName ]
                    xHtmlTag.mDictionary = xResponse['return']['value']                                
                    xHtmlTag.mObject     = xObject
                    self.mGlobals[xName] = xObject
            except Exception as xEx:
                pass
                
        except AttributeError as xEx:
            xCell = TCell(0, 409, [xCallPath])
            self.mTraceStack.append(list(), xCell)
        except Exception as xEx:
            xCell = TCell(0, 610, [xCallPath, str(xEx)])
            self.mTraceStack.append(list(), xCell)
    
    # --------------------------------------------------------
    # --------------------------------------------------------
    def evalTraceReturn(self, aJsonObj): 
        xDatabase = self.mGlobals.get('eezzAgent.database')
        
        if xDatabase != None and len(self.mTraceStack) > 0:
            xDatabase         = self.mGlobals.get('eezzAgent.database')
            xDatabase         = self.mElements.get(xDatabase.get('name'))
            xDatabase.mObject = self.mTraceStack
            self.generateTableSegment(None, xDatabase, xDatabase.get('name'))            
            xDatabase.mChildren.clear()
            self.mTraceStack.clear()
            
            return xDatabase
    
    # --------------------------------------------------------
    # Work with web-socket requests     
    # --------------------------------------------------------
    def handle_websocket(self, aJsonObj, aSession = True):
        # prepare file download  
        if aJsonObj and aJsonObj.get('callback'):
            print('command : ', aJsonObj.get('callback'))      
        if 'files' in aJsonObj.keys():
            try:        
                xClassName, xMethodName = aJsonObj['reader'].split('.') 
                xMethod   = getattr(self.mGlobals.get(xClassName), xMethodName)
                xResponse = xMethod(aJsonObj, None)
            except AttributeError:
                pass            

        # normal processing
        if 'path' in aJsonObj: 
            if self.mCurrentDocument == None:
                xPath = aJsonObj['path']
                if xPath[0] in ['/', '\\']:
                    xPath = xPath[1:]

                if not xPath:
                    self.mCurrentDocument = os.path.join( self.mBlackboard.mDocRoot, 'index.html' )                                    
                else:
                    self.mCurrentDocument = os.path.join( self.mBlackboard.mDocRoot, xPath )                                    

            if aJsonObj.get('args'):
                xJsonStr = urllib.parse.unquote(aJsonObj['args'])
                self.mArguments = json.loads(xJsonStr)
                pass
        
        # execute the parser as session
        try:
            # Evaluate WebSocket 
            xResponse = self.handle_request(self.mCurrentDocument, None, aSession, aJsonObj)
        except Exception as xEx:
            pass
            raise xEx

        
        with self.mLock:
            if 'reconnect' in aJsonObj or 'video' in aJsonObj:
                return
            
            # The name of body is collected during the request
            if 'path' in aJsonObj: 
                xDict = aJsonObj.get('update',  {})
                xDict.update({self.mUpdateBody + ".innerHTML":"*"})
                aJsonObj['update'] = xDict


            xDatabase    = self.evalTraceReturn( aJsonObj )
            xTraceUpdate = dict()
            if xDatabase:
                xTraceUpdate['update'] = {xDatabase.get('name') + '.innerHTML':'*'}

            # Nothing to update,- so we could return here
            if 'update' not in aJsonObj:
                return None
            
            # put the section for update into the json request
            try:
                xJsonResult = dict()
                xJsonResult['update']      = dict()
                xJsonResult['updateValue'] = dict()
                                
                xKeyList = list(aJsonObj['update'].keys())
                if xTraceUpdate.get('update'):
                    for xKey, xValue in xTraceUpdate['update'].items():
                        aJsonObj['update'][xKey] = xValue
                        xKeyList.append(xKey)
                
                for xKey in xKeyList:
                    xValue = aJsonObj['update'][xKey]
                    xDstFields = xKey.split('.')
                    xSrcFields = xValue.split('.')
                    xHtmlTag   = None
                    xSrcName, xSrcAttr, xId = None, None, None
                    xUpdateFromServer = False
                    
                    # '*' for value would copy the key for the value specification
                    # The format "name.attribute" copies the [attribute] of HTML-tag [name]
                    if xValue == '*':
                        xUpdateFromServer = True
                        xSrcFields = xDstFields
                    
                    if len(xSrcFields) == 2:
                        xSrcName, xSrcAttr = xSrcFields
                        xHtmlTag  = self.mElements.get(xSrcName)
                    elif len(xSrcFields) == 3:
                        xSrcName, xSrcAttr, xId = xSrcFields
                        xHtmlTag  = self.mElements.get(xSrcName)
                    
                    # - if no HTML tag as source was found, send the [value] itself as update
                    # - for innerHTML send the parser result for the fragment
                    # - find the xSrcAttr attribute for xValue == '*'
                    # - evaluate the update value from HTML page
                    if xHtmlTag == None:
                        xJsonResult['update'][xKey] = urllib.parse.quote(xValue)
                        continue
                    
                    if xSrcAttr == 'innerHTML':
                        xEntry = xKey
                        #if xHtmlTag.get('class') == 'eezzTreeNode':
                        #    xNodeId = xHtmlTag.get('id')
                        #    xEntry  = '{}.{}'.format(xKey, xNodeId)
                        xJsonResult['update'][xEntry] = urllib.parse.quote( xHtmlTag.mInnerHtml.getvalue() )
                        continue
                    
                    if xUpdateFromServer:
                        if xSrcAttr and xHtmlTag.get(xSrcAttr):
                            xValue = xHtmlTag.get(xSrcAttr).encode('utf-8')
                            xJsonResult['update'][xKey]  = urllib.parse.quote(xValue)
                    elif len(xSrcFields) > 1:
                        xServerValue = xHtmlTag.get(xSrcAttr)
                        xJsonResult['update'][xKey] = urllib.parse.quote(xServerValue)
            except (KeyError, AttributeError) as aEx:
                print('key error:' + str(aEx))            
            
            # send the response
            aJsonObj['update']      = xJsonResult['update']
            aJsonObj['updateValue'] = xJsonResult['updateValue']
            
            return json.dumps(aJsonObj)
            
    # --------------------------------------------------------
    # The method asyncResponse is designed to run in an own
    # thread. It executes a given JSON-callback and send the
    # changes to the UI.
    # --------------------------------------------------------
    def async(self):
        while True:
            xInterest = self.mBlackboard.getInterest(self.mCookie)
            if xInterest:
                xUpdate   = dict()
                xUpdate.update(self.mUpdateVector)
                xJsonResp = self.handle_websocket({'update':xUpdate}, False)
                self.mWebClient.writeFrame( xJsonResp.encode('utf8') )
            
            if self.mEvent.wait(4):
                break
            
    # --------------------------------------------------------
    # Stops all asynchronous threads
    # --------------------------------------------------------
    def shutdown(self):
        self.mBlackboard.delInterest(self.mCookie)
        self.mEvent.set()
        if self.mAsyncThr != None:
            self.mAsyncThr.join()
    
    # --------------------------------------------------------
    # Work with HTTP server requests
    # --------------------------------------------------------
    def handle_request(self, aFile, aForm=None, aSession=False, aJsonObj=None):
        aParent  = self.mTagStack[0]
        try:     
            if aJsonObj:
                self.jsonCallback(aJsonObj)
 
            with self.mLock:                    
                if aJsonObj and aJsonObj.get('arguments'):
                    self.mArguments =  aJsonObj.get('arguments')

                self.mSession         = aSession
                self.mCurrentDocument = aFile
                        
                aParent.mInnerHtml = io.StringIO()        
                with open(self.mCurrentDocument, 'r') as aFile:
                    for xContent in aFile:
                        self.feed(xContent)
                
                # At this point the stack has to be finished
                if len(self.mTagStack) > 1:
                    xTag = self.mTagStack[-1]
                    xLine, xOffset = self.getpos()
                    xCell = TCell(0, 605, [str(xLine), str(xOffset), xTag.mTagName, "EndOfFile"])
                    self.mTraceStack.append(list(), xCell) 
        
                # close all open tags to present something
                while len(self.mTagStack) > 1:
                    xTag = self.mTagStack[-1]
                    self.handle_endtag(xTag.mTagName)
                    
                self.reset()        
                xResult = aParent.mInnerHtml.getvalue()
    
                return xResult
        except Exception as xEx:
            raise xEx
            
    # --------------------------------------------------------
    # Change the web-socket client address
    # --------------------------------------------------------
    def setClientAddr(self, client_address):
        self.mCltAddr = client_address
                
    # --------------------------------------------------------
    # Show the evaluated HTML document 
    # --------------------------------------------------------
    def dump(self):
        aParent  = self.mTagStack[0]
        print(aParent.getvalue())
        with open('agenttest.html', 'w') as aFile:
            aFile.write(aParent.mInnerHtml.getvalue())
            
    # --------------------------------------------------------
    # Find attribute for a named element: <element>.<attribute>
    # --------------------------------------------------------
    def findTagAttr(self, aValue):
        xElem, xAttr = aValue.split('.')
        
        xObj = self.mGloabls.get(xElem)
        if xObj == None:
            return None
        
        if isinstance(xObj, THtmlTag):
            return xObj.get(xAttr)            
        else:
            xObj = xObj.mEasyTag
            return xObj.get(xAttr)
          
    # --------------------------------------------------------
    # Find an element by name in the given hierarchy
    # --------------------------------------------------------
    def findElement(self, aName):
        for xElem in reversed(self.mTagStack):
            if xElem.get('name') == aName:
                return xElem
        return None

    # --------------------------------------------------------
    # Find an element by name in the given hierarchy
    # --------------------------------------------------------
    def findTmplRoot(self, aElement = None):
        for xElem in reversed(self.mTagStack):
            if xElem.mTagName in ['tr', 'select']:
                if xElem.mTemplate:
                    for x, y in xElem.mTemplate.items():
                        if x in ('table-rows', 'table-columns'):
                            return xElem
                        if x == 'display' and ('type' in y or 'status' in y):
                            return xElem                    
        return None

    # --------------------------------------------------------
    # Find an element by name in the given hierarchy
    # --------------------------------------------------------
    def findElementByAttr(self, aAttribute, aElement = None):
        if aElement and aAttribute in aElement:
            return aElement
        
        for xElem in reversed(self.mTagStack):
            if aAttribute in xElem:
                return xElem
        return None

    # --------------------------------------------------------
    # Find an element by name in the given hierarchy
    # --------------------------------------------------------
    def findTagElement(self, aNameSet):
        for xElem in reversed(self.mTagStack):
            if xElem.mTagName in aNameSet:
                return xElem
        return None

    # --------------------------------------------------------
    # Find an element by name in the given hierarchy
    # --------------------------------------------------------
    def findDictionary(self, aElem = None):
        if aElem and aElem.mDictionary:
            return aElem.mDictionary
        
        for xElem in reversed(self.mTagStack):
            if xElem.mDictionary:
                return xElem.mDictionary
        return dict()
    
    # --------------------------------------------------------
    # Set the new language
    # --------------------------------------------------------
    def set_language(self, language='en_EN'):
        xLocaleDir     = os.path.join('..','resources', 'locales')
        self.mLanguage = gettext.translation(self.mCurrDomain, localedir=xLocaleDir, languages=[language])
        
    # --------------------------------------------------------
    # Find command and format attributes
    # format attributes reference the context of the current scope
    # format specification covers all embedded tags          
    # -------------------------------------------------------- 
    def handle_starttag(self, aTagName, aAttrs):  
        aParent     = self.mTagStack[-1]
        aSession    = self.mSession
        aHtmlTag    = None
        xName       = None
        
        xDictAttr = {xKey:xVal for xKey, xVal in aAttrs}
        xName     = xDictAttr.get('name')

        if aTagName == 'body':
            self.mUpdateBody = xDictAttr.get('name', '_body_')
            xName = self.mUpdateBody

        if xName:
            aHtmlTag = self.mElements.get(xName)
                        
        if aHtmlTag == None:
            aHtmlTag = THtmlTag(aTagName)
        
        if xName:
            self.mElements[xName] = aHtmlTag
            aHtmlTag['name'] = xName            
                    
        aHtmlTag.mInnerHtml = io.StringIO()
                        
        xLine, xOffset = self.getpos()
        # print('start {}'.format(aTagName))
                
        for xKey, xValue in xDictAttr.items():
            #-- print('process start {} - {} {}'.format(aTagName, xKey, xValue))
            if xKey in ['data-eezz-action', 'data-eezz-event']:
                try:
                    xJsonObj = json.loads(xValue.replace('\'', '\"'))
                except ValueError as aEx:
                    self.mTraceStack.append(aCell=TCell(aType=601, aObject=[str(xLine), str(xOffset), xKey, xValue])) 
                    continue
                except Exception as aEx:
                    continue
                
                if aHtmlTag.mJsonObj:    
                    aHtmlTag.mJsonObj.update( xJsonObj )
                else:
                    aHtmlTag.mJsonObj = xJsonObj 
                
                if aTagName == 'tr':
                    pass
                
                # insert the query as callback and asign argument                
                if aSession:
                    for xArgKey in xJsonObj.keys():                    
                        if xArgKey in ('eezzAgent.assign', 'callback'):  
                            for x1, y1 in xJsonObj[xArgKey].items():                            
                                for x2, y2 in y1.items():
                                    if isinstance(y2, str) and y2.startswith('eezzQuery.'):
                                        if self.mArguments and self.mArguments.get(y2.split('.')[1]):
                                            xReplaceArgs = self.mArguments.get(y2.split('.')[1])
                                            xJsonObj[xArgKey][x1][x2] = xReplaceArgs[0]
                                        else:
                                            xJsonObj[xArgKey][x1][x2] = None
                
                aHtmlTag[xKey] = urllib.parse.quote(json.dumps(xJsonObj))
                                        
                if ('eezzAgent.assign' in xJsonObj or 'eezzAgent.async' in xJsonObj) and aSession:
                    xAsignStm = dict()
                    xAsignStm.update(xJsonObj.get('eezzAgent.assign', dict())) 
                    xAsignStm.update(xJsonObj.get('eezzAgent.async', dict())) 

                    for x1, y1 in xAsignStm.items():
                        xPathClass = x1
                        xCallParam = y1
                        break;

                    if self.mGlobals.get(xName) != None:
                        if not isinstance(self.mGlobals.get(xName), TTable):
                            continue

                    xRoot      = os.path.join( os.path.split(os.getcwd())[0], 'applications' )                                                            
                    xPathParts = xPathClass.replace('/', os.path.sep).rsplit(os.path.sep, 2)

                    if len(xPathParts) == 3:
                        xPath, xModName, xClassName = xPathParts
                        xPath  = os.path.join(xRoot, xPath)
                        xClass = None
                        
                        if not os.path.isdir(xPath):
                            self.mTraceStack.append(aCell=TCell(aType=602, aObject=[str(xLine), str(xOffset), xPath])) 
                            continue
                        
                        if xPath not in sys.path:
                            sys.path.append(xPath)
                        
                        xPath = os.path.split(xPath)
                        if xPath not in sys.path:
                            sys.path.append(xPath[0])
                        
                        if not self.mGlobals.get(xClassName):
                            try:
                                xModule = importlib.import_module(xModName)
                                xClass  = getattr(xModule, xClassName)
                            except Exception as xEx:
                                xCell = TCell(0, 610, [xPathClass, str(xEx)])
                                self.mTraceStack.append(list(), xCell) 
                                continue
                            else:
                                self.mGlobals[xClassName] = xClass
                        
                        if not self.mGlobals.get(xName):
                            xClass  = self.mGlobals[xClassName]
                            xObject = xClass(**xCallParam)
                            self.mGlobals[xName] = xObject

                        aHtmlTag.mObject = self.mGlobals[xName]

                    elif len(xPathParts) == 2:
                        xModName, xClassName = xPathParts
                        xClass = None
                        
                        if not self.mGlobals.get(xClassName):
                            try:
                                xModule = importlib.import_module(xModName)
                                xClass  = getattr(xModule, xClassName)
                                self.mGlobals[xClassName] = xClass
                                self.mGlobals[xName]      = xClass(**xCallParam)
                            except Exception as xEx:
                                self.mTraceStack.append(aCell=TCell(aType=610, aObject=['.'.join(xPathParts), str(xEx)]))                                 
                            else:
                                aHtmlTag.mObject = self.mGlobals[xName]
                        
                    elif len(xPathClass.split('.')) == 2:
                        xClassName, xMethodName = xPathClass.split('.')
                        if self.mGlobals.get(xClassName):
                            aService = self.mGlobals.get(xClassName)
                            xMethod  = getattr(self.mGlobals.get(xClassName), xMethodName)

                            try:
                                xResponse = xMethod(**xCallParam)
                            except Exception as xEx:
                                # Class or method not found
                                self.mTraceStack.append(aCell=TCell(aType=610, aObject=['.'.join(xPathParts), str(xEx)]))                                 
                            else:
                                if xResponse['return']['code'] == 200:
                                    aHtmlTag.mObject = xResponse['return']['value']
                            
                                if ('eezzAgent.async' in xJsonObj):
                                    self.mBlackboard.addInterest(self.mCookie)
                                    if self.mAsyncThr == None or not self.mAsyncThr.is_alive():
                                        self.mAsyncThr = threading.Thread(target=self.async)
                                        self.mAsyncThr.start()
                                    if xJsonObj.get('update'):
                                        self.mUpdateVector.update(xJsonObj.get('update'))
                                    
                                self.mGlobals[xName] = aHtmlTag.mObject
                    if aHtmlTag.mObject != None:
                        xResponse = aHtmlTag.mObject.get_dictionary()
                        if xResponse['return']['code'] == 200:
                            aHtmlTag.mDictionary = xResponse['return']['value']

                                                        
                if 'eezzAgent.dictionary' in xJsonObj:
                    xDictClass, xDictMethod = xJsonObj['eezzAgent.dictionary'].split('.')
                    xObject = None
                    try:
                        xObject   = self.mGlobals[xDictClass]
                        xMethod   = getattr(xObject, xDictMethod)
                        xResponse = xMethod()
                        aHtmlTag.mDictionary = xResponse['return']['value']
                    except (KeyError, AttributeError, IndexError) as aEx:
                        self.mTraceStack.append(aCell=TCell(aType=603, aObject=[str(xLine), str(xOffset), xDictClass, xDictMethod])) 
            
        for xKey, xValue in xDictAttr.items():
            if xKey == 'data-eezz-template':
                if xValue == 'database':
                    self.mGlobals['eezzAgent.database'] = aHtmlTag
                    aHtmlTag.mChildren.clear()
                elif xValue == 'template':
                    aHtmlTag.mChildren.clear()
                else:
                    try:
                        aHtmlTag.mTemplate = json.loads(xValue.replace('\'', '\"'))
                    except ValueError as xEx:
                        self.mTraceStack.append(aCell=TCell(aType=601, aObject=[str(xLine), str(xOffset), xKey, xValue])) 
                        continue
            
            if aTagName == 'table' and aHtmlTag.get('name'):
                aHtmlTag.mDictionary['name'] = aHtmlTag.get('name')
                            
            if not xKey in ['data-eezz-action', 'data-eezz-event']:
                try:
                    if aHtmlTag.mDictionary:
                        xDictionary = aHtmlTag.mDictionary
                    else:
                        xDictionary = self.findDictionary()
                    aHtmlTag[xKey]  = xValue.format(**xDictionary)
                except (KeyError, TypeError, IndexError) as xEx:
                    aHtmlTag[xKey]  = xValue
                except Exception as aEx:
                    self.mTraceStack.append(aCell=TCell(aType=604, aObject=[str(xLine), str(xOffset), xKey, xValue])) 
        
        self.mTagStack.append(aHtmlTag)
        if self.findTmplRoot() != None:
            aParent.mChildren.append(aHtmlTag)
    
    # --------------------------------------------------------
    # Execute the EEZZ server page commands
    # --------------------------------------------------------
    def handle_endtag(self, aTagName):
        if len(self.mTagStack) < 2:
            return

        xTemplRoot = self.findTmplRoot()
        aHtmlTag   = self.mTagStack.pop()
        aParent    = self.mTagStack[-1]
        xTableTag  = self.findTagElement(('table',))
     
        xLine, xOffset = self.getpos()
        if aHtmlTag.mTagName != aTagName:
            xCell = TCell(aType=605, aObject=[str(xLine), str(xOffset), aTagName, aHtmlTag.mTagName])
            self.mTraceStack.append(list(), xCell)
        
        try:           
            # Inherit the dictionary from parent table tag
            if aTagName in ['caption', 'tr', 'td', 'th', 'tbody', 'thead', 'tfoot']:
                aHtmlTag.mDictionary = self.findDictionary()
                if xTableTag.mObject and not aHtmlTag.mDictionary:
                    aHtmlTag.mDictionary = xTableTag.mObject.get_header()

            if aParent.get('data-eezz-template') == 'database':
                return
            if aHtmlTag.get('data-eezz-template') == 'database':
                xHtmlTag = THtmlTag(aHtmlTag.mTagName)
                xHtmlTag.update(aHtmlTag)
                aHtmlTag = xHtmlTag
            
            if aHtmlTag.get('data-eezz-template') == 'template':
                return
            
            if xTemplRoot != None:
                return

            if aHtmlTag.mTemplate:
                if isinstance(aHtmlTag.mTemplate.get('display'), dict):
                    for x, y in aHtmlTag.mTemplate.get('display').items():
                        if not aHtmlTag.mDictionary.get(x, 'default') in y:
                            return
                    pass
                #if aHtmlTag.mTemplate.get('display') == 'template':
                #    aParent = None
                    
            if len(aHtmlTag.mChildren) > 0:
                if aHtmlTag.mTagName in ['tfoot','thead','tbody']:
                    self.generateTableSegment( aParent, aHtmlTag, aParent.get('name') )
                    aHtmlTag.mChildren.clear()
                else:
                    aHtmlTag.mInnerHtml = io.StringIO()
                    for xElem in aHtmlTag.mChildren:
                        if xElem.mTagName == 'select':
                            xElem.mInnerHtml = io.StringIO()
                            self.generateTableSegment( aHtmlTag, xElem, xElem.get('name') )
                            xElem.mChildren.clear()
                        elif xElem.mTagName == 'table':
                            self.generateTableSegment( aHtmlTag, xElem, xElem.get('name') )
                    aHtmlTag.mChildren.clear()
                    self.generateHtml(aParent, aHtmlTag)
            else:
                if xTableTag and xTableTag.mObject:
                    self.generateHtml(aParent, aHtmlTag, None, xTableTag.mObject.mHeaderDic)
                else:
                    self.generateHtml(aParent, aHtmlTag, None, None)
                                        
        except Exception as xEx:
            raise
            pass
        
        if aTagName != aHtmlTag.mTagName:
            self.mTraceStack.append(aCell=TCell(aType=605, aObject=[str(xLine), str(xOffset), aHtmlTag.mTagName, aTagName])) 
                        
    
    # --------------------------------------------------------
    # Handle data section
    # --------------------------------------------------------
    def handle_data(self, aData):
        aParent         = self.mTagStack[-1]
        aDictionary     = self.findDictionary()

        if aParent.mTagName == 'style':
            aParent.mInnerHtml.write(aData)
            return
        
        try:
            xData = aData.format(**aDictionary)
        except (KeyError, TypeError, IndexError):
            xData = aData
        except (ValueError):
            raise
        
        xResult = re.sub(r'_\("([\w%-{}! ]+)"\)', self.doTranslate, xData)        

        if self.findTmplRoot() != None:
            xHtmlTag = THtmlTag('cdata')
            xHtmlTag.mValue = xResult
            aParent.mChildren.append(xHtmlTag)
            return;

        aParent.mInnerHtml.write(xResult)
            
    # --------------------------------------------------------
    # Remove comments
    # --------------------------------------------------------
    def handle_comment(self, aData):
        pass    

    # --------------------------------------------------------
    # --------------------------------------------------------
    def handle_charref(self, aData):
        aParent  = self.mTagStack[-1]
        aParent.mInnerHtml.write('&#{};'.format(aData))
        pass
    # --------------------------------------------------------
    # Transfer declaration
    # --------------------------------------------------------
    def handle_decl(self, aData):
        aParent = self.mTagStack[-1]
        aParent.mInnerHtml.write('<!{0}>'.format(aData))
    
    # --------------------------------------------------------
    # Callback for re.sub in handle_data
    # Translates strings of format '_(' <string> ')'
    # --------------------------------------------------------
    def doTranslate(self, aMatchObj):
        aText  = aMatchObj.group(1)

        if '&' in aText:
            pass
        
        if self.mLanguage != None:
            aText = self.mLanguage.gettext(aText)
        else:
            aText = gettext.gettext(aText)

        return aText

    # --------------------------------------------------------
    # Generate java script
    # --------------------------------------------------------
    def get_script(self):
        aWebSocketHeader = """
            var gSocketAddr     = "ws://{}:{}";
            var eezzWebSocket   = "" /* = new WebSocket(gSocketAddr) */;
            var eezzArguments   = "";
            """
        if self.mArguments:
            aWebSocketHeader += "\neezzArguments = \"" + urllib.parse.quote(json.dumps(self.mArguments)) + "\";\n";
            pass
        
        aWebSocketScript = ""
        xResoucePath     = os.path.join('..', 'resources', 'websocket.js')

        try:
            with open(xResoucePath, 'r') as xFile:
                aWebSocketScript = xFile.read()
        except Exception as xEx:
            print(xEx)
            
        xHost, xPort = self.mCltAddr
        xText = '{}\n{}'.format(aWebSocketHeader.format(xHost, xPort), aWebSocketScript)
        return {'return':{'code':200, 'value': {'websocket': xText} }}

    # --------------------------------------------------------
    # --------------------------------------------------------
    def service(self, aServiceName, aServiceWord):
        try:
            xResponse = {'return':{'code':200, 'value':'OK'}} 
            if aServiceName == 'system':
                if aServiceWord == 'shutdown':
                    return {"return":{"code":200, "value":"OK"}}
                return {"return":{"code":527, "value":"unknown service", "args":[aServiceName]}}
            
            #xService      = xServiceAdmin.getService(aServiceName)
            #xResponse     = xService.do_request(aServiceWord)
            return xResponse
        except Exception as xEx:
            return {"return":{"code":528, "value":"service failed", "args":[aServiceName, aServiceWord, str(xEx)]}}

    # --------------------------------------------------------
    # --------------------------------------------------------
    def evalRange(self, aNamedRange, aNames):
        xRegRange   = re.compile('([0-9]*):([0-9]*)')
        xMatchRange = xRegRange.match(aNamedRange[0])
        xNameInx    = list()
        
        if aNamedRange[0] == ':':
            for i in range(len(aNames)):
                xNameInx.append(i)                     
        elif xMatchRange:                            
            xStart, xEnd = (0, len(aNames))
            if xMatchRange.group(1):
                xStart = max(0, min(xEnd, int(xMatchRange.group(1))))
            if xMatchRange.group(2):
                xEnd   = max(0, min(xEnd, int(xMatchRange.group(2))))
                
            for i in range(xStart, xEnd):
                xNameInx.append(i)
        else:
            for i in aNamedRange:
                if i in aNames:
                    xNameInx.append(aNames.index(i))
        return xNameInx

    # --------------------------------------------------------
    # --------------------------------------------------------
    def generateTableRow(self, aParent, aHtmlTag, aColumnNames, aJsnColEvt):
        xTblRow     = aHtmlTag
        xColumnList = list()
        xColumnInx  = list()
        xTemplates  = list()
        xPrintCols  = list()
        xTblRow.mInnerHtml = io.StringIO()
        aTblId, aColCmd    = None, None
        
        for xKey, xValue in xTblRow.items():
            if not isinstance(xValue, str):
                continue
            if not xKey in ['data-eezz-event', 'data-eezz-action','data-eezz-template']:
                try:
                    xValue = html.escape(xValue)
                    xValue = xValue.replace('{', '&lbrace;')
                    xValue = xValue.replace('}', '&rbrace;')
                    xTblRow[xKey] = xValue.format(**xTblRow.mDictionary)
                except Exception as xEx:
                    raise
                
        if aJsnColEvt:
            aTblName, aTblId, aColCmd = aJsnColEvt

        # Collect variants and collect update on a named status variable
        for xTd in xTblRow.mChildren:
            xUpdate = None
            
            if aTblId and xTd.get('name'):
                xSubId    = urllib.parse.quote( 'status@' + aTblId )
                xUpdate   = {aTblName + '.innerHTML.' + xSubId: '*'} 
                xTd['id'] = xSubId

            if xTd.mTagName in ['td', 'th'] and xTd.mTemplate.get('display'):
                for xKey, xValue in xTd.mTemplate.get('display').items():
                    if xKey == 'status' and xTblRow.mValue and isinstance(xTblRow.mValue[0], TCell):
                        xCell = xTblRow.mValue[0]
                        if xValue == xCell.mStatus:
                            xColumnList.append(xTd)
                            
                            xSubId    = urllib.parse.quote( 'status@' + aTblId )
                            xUpdate   = {aTblName + '.innerHTML.' + xSubId: '*'} 
                            xTd['id'] = xSubId

                            xCell.mObject['update'] = xUpdate
                    else:
                        xTemplates.append([xKey, xValue, xTd])
            else:
                xColumnList.append(xTd)
                
        # Calculate the update for a sort command
        if aJsnColEvt:
            aTblName, aTblId, aColCmd = aJsnColEvt
            if aTblId:
                xSubId  = urllib.parse.quote( aTblId )
                xUpdate = {aTblName + '.innerHTML.' + xSubId: '*'} 
            else:
                xUpdate = {aTblName + '.innerHTML': '*'} 
                

        for xTd in xColumnList: 
            if xTblRow.mTagName == 'option':
                xTd.mTemplate = xTblRow.mTemplate
                #xTd.mValue    = xTblRow.mValue
                pass
            else:
                if not xTd.mTagName in ['td', 'th']:
                    continue
                                
            if xTd.mTemplate.get('table-columns') and aColumnNames:
                xNamedRange = xTd.mTemplate.get('table-columns')
                xColumnInx  = self.evalRange(xNamedRange, aColumnNames)
                
                for i in xColumnInx:
                    xTdSave = xTd
                    if isinstance(xTblRow.mValue[i], TCell):
                        xCell  = xTblRow.mValue[i]
                        xEntry = [x[2] for x in xTemplates if x[0] == 'type' and x[1] == xCell.mType]
                        if xEntry:
                            xTdSave = xEntry[0]
                               
                    xTdTemplate = THtmlTag(xTdSave.mTagName) 
                    xTdTemplate.update(xTdSave)
                    xTdTemplate.mChildren = xTdSave.mChildren
                    xTdTemplate.mJsonObj  = xTdSave.mJsonObj
                    
                    if xTdSave.mTagName == 'cdata':
                        xTdTemplate.mValue = xTdSave.mValue
                    
                    if aColCmd:
                        xEvent  = {'callback': {'{}.{}'.format(aTblName, aColCmd) : {'index': str(i)}}, 'update': xUpdate}                                    
                        xTdTemplate['data-eezz-event'] = urllib.parse.quote( json.dumps(xEvent) )

                    xTdTemplate.mColumnInx = i
                    xPrintCols.append(xTdTemplate)
            else:
                xTdSave = xTd                            
                xTdTemplate = THtmlTag(xTdSave.mTagName) 
                xTdTemplate.update(xTdSave)
                xTdTemplate.mChildren = xTdSave.mChildren
                xTdTemplate.mJsonObj  = xTdSave.mJsonObj
                
                if xTdTemplate.mTagName == 'cdata':
                    xTdTemplate.mValue = xTdSave.mValue
                
                xPrintCols.append(xTdTemplate)


        for xTd in xPrintCols:
            xValueList     = list()
            xTd.mInnerHtml = io.StringIO()
             
            if xTd.mColumnInx and xTblRow.mValue:
                xValueList += [ str(xTblRow.mValue[ xTd.mColumnInx ]) ]
            if xTblRow.mValueList and xTblRow.mValueList:
                xValueList += xTblRow.mValueList
                 
            self.generateHtml(xTblRow, xTd, xValueList, xTblRow.mDictionary) 
            
    # --------------------------------------------------------
    # --------------------------------------------------------
    def generateTableSegment(self, aParent, aHtmlTag, aTableName):  
        xTableTag    = aParent
        xTableSeg    = aHtmlTag
        xRowList     = list()
        xTemplates   = list()
        xTable       = None
        xColumnNames = None
        
        if xTableTag == None:
            xTableTag = xTableSeg
        
        if xTableSeg.mTagName == 'select':
            xTable        = xTableSeg.mObject
            xTblName      = aTableName
        elif xTableSeg.mTagName == 'table':
            xTable        = xTableSeg.mObject
            xTblName      = aTableName
        else:
            xTable    = xTableTag.mObject
            xTblName  = xTableTag.get('name')
                      
        xTableSeg.mInnerHtml = io.StringIO()

        if xTable == None:
            xTable    = xTableTag.mObject
            xTblName  = xTableTag.get('name')
            
        if xTable != None:
            xColumnNames  = xTable.get_columns()[0]
            xTable.hasChanged()
            
        xTblUpdate = dict()
        if xTableTag.mJsonObj and xTableTag.mJsonObj.get('update'):
            xTblUpdate.update( xTableTag.mJsonObj.get('update') )
        
        # Remove elements                
        for xTr in xTableSeg.mChildren:
            if not xTr.mTagName in ['tr', 'option']:
                continue
                        
            if xTr.mTagName == 'option':
                xTr.mTemplate.update(xTableSeg.mTemplate)
            
            # A display attribute could reference the dictiponary or the value 
            # list in the TCell object
            if xTr.mTemplate.get('display'):
                for xKey, xValue in xTr.mTemplate.get('display').items():
                    xTemplates.append([xKey, xValue, xTr])
            else:
                xRowList.append(xTr)
        
        xTreeId = None
        if xTable != None and xTableTag.get('class') in ['eezzTreeNode', 'eezzTreeLeaf']:
            xTreeId = '{}:{}'.format(xTblName, xTable.mPath)
        
        for xTr in xRowList:
            if xTable == None:
                self.generateTableRow(xTableSeg, xTr, None, None)
                xTableSeg.mInnerHtml.write( xTr.generateHtml() )
                continue
            
            if 'table-rows' in xTr.mTemplate:                    
                if xTableSeg.mTagName == 'thead':
                    xTrTemplate = THtmlTag(xTr.mTagName)
                    xTrTemplate.update(xTr)                 
                    xTrTemplate.mJsonObj  = xTr.mJsonObj
                    xTrTemplate.mChildren = xTr.mChildren
                    xTrTemplate.mValue    = xColumnNames
                    xTrTemplate.mDictionary.update(xTableSeg.mDictionary)            
                    self.generateTableRow(xTableSeg, xTrTemplate, xColumnNames, (xTblName, xTreeId, 'do_sort'))
                    xTableSeg.mInnerHtml.write( xTrTemplate.generateHtml() )
                else:
                    for xInx, xRows in enumerate(xTable.get_raw_rows()):
                        xTrSave = xTr
                        xCell   = xRows[0]                        
                        xEvent  = dict()  
                        xTblDic = dict()
                        if len(xRows) > 1 and isinstance(xRows[1], TTable):
                            xTblDic = xRows[1].mHeaderDic
                            
                        if isinstance(xCell, TCell):
                            xEntry = [x[2] for x in xTemplates if x[0] == 'type' and x[1] == xCell.getType()]
                            if xEntry:
                                xTrSave     = xEntry[0]
                                xTrTemplate = THtmlTag(xTrSave.mTagName)
                                xTrTemplate.mDictionary.update(xTableSeg.mDictionary) 
                                           
                                if isinstance(xCell.getObject(), dict):
                                    xTrTemplate.update(xCell.getObject())
                                if isinstance(xCell.getObject(), list):
                                    xTrTemplate.mValueList = xCell.getObject()
                            else:
                                xTrTemplate = THtmlTag(xTrSave.mTagName)
                                xTrTemplate.update(xTrSave)
                        else:
                            xTrTemplate = THtmlTag(xTrSave.mTagName)
                            xTrTemplate.update(xTrSave)
                                
                        xTrTemplate.mJsonObj    = xTrSave.mJsonObj
                        xTrTemplate.mChildren   = xTrSave.mChildren
                        xTrTemplate.mValue      = xRows
                        xTrTemplate.mDictionary.update(xTableSeg.mDictionary)            
                            
                        xEvtUpdate = dict()
                        xTrsUpdate = dict()
                        if xTrTemplate.mJsonObj:
                            xTrsUpdate = xTrTemplate.mJsonObj.get('update', xTrsUpdate)
                        
                        if xTrSave.get('class') in ['eezzTreeNode', 'eezzTreeLeaf']:
                            if isinstance(xRows[1], TTable):
                                xSubTreeId = '{}:{}'.format(xTblName, xRows[1].mPath)
                            else:
                                xSubTreeId = xTreeId
                                                              
                            xSubTreeQt = urllib.parse.quote( xSubTreeId )
                            xValue     = xTrsUpdate.get('this'+'.innerHTML', '*') 
                            # xTreeId1    = 'id{}'.format(uuid.uuid1().time_low)
                            if xTrSave.get('class') == 'eezzTreeNode':
                                xEvtUpdate = {'{}.innerHTML.{}'.format(xTblName, xSubTreeQt): xValue}                        
                                xEvtUpdate.update( xTblUpdate )
                            xTrTemplate['id']    = xSubTreeQt
                            xTrTemplate['class'] = xTrSave.get('class')

                        if xTrSave.get('class') == 'eezzTreeLeaf':
                            if xTable and xInx == xTable.get_selected_index():
                                xTrTemplate['class'] = ' '.join(['eezzTreeLeaf','eezzSelected']) 
                            
                        if xTrSave.mJsonObj and xTrSave.mJsonObj.get('callback'):
                            xEvtUpdate.update( xTblUpdate )
                            xEvent['callback'] = xTrSave.mJsonObj.get('callback')
                            xEvent['update']   = xEvtUpdate
                        else:
                            xEvtUpdate.update( xTblUpdate )
                            xEvent['callback'] = {'{}.do_select'.format(xTblName) : {'index': str(xRows[0])}}
                            xEvent['update']   = xEvtUpdate                                    
            
                        if xTrSave.mTagName == 'option':
                            if xTableSeg.mJsonObj.get('update'):
                                xEvtUpdate = xTableSeg.mJsonObj.get('update')
                            xEvtUpdate.update( xTblUpdate )
                            xEvent['update'] = xEvtUpdate
                            xTrTemplate['data-eezz-event'] = urllib.parse.quote( json.dumps( xEvent) )
                            xTrTemplate.mTemplate = xTrSave.mTemplate

                            if xTable:
                                if xInx == xTable.get_selected_index():
                                    xTrTemplate['selected'] = 'selected'
                                elif xTrTemplate.get('selected'):
                                    del xTrTemplate['selected']                                    
                            self.generateTableRow(xTableSeg, xTrTemplate, xColumnNames, None)
                            xTableSeg.mInnerHtml.write( xTrTemplate.generateHtml() )
                        else:
                            xTrTemplate['data-eezz-event'] = urllib.parse.quote( json.dumps( xEvent) )
                            self.generateTableRow(xTableSeg, xTrTemplate, xColumnNames, (xTblName, xTreeId, None))
                            xTableSeg.mInnerHtml.write( xTrTemplate.generateHtml() )

        if aParent != None:
            aParent.mInnerHtml.write( aHtmlTag.generateHtml() )

    
    # --------------------------------------------------------
    # --------------------------------------------------------
    def generateHtml(self, aParent, aElement, aArgsList = None, aDictionary = None):
        if aElement.get('data-eezz-template'):
            del aElement['data-eezz-template']
        
        #aElement.mInnerHtml = io.StringIO()
                    
        for xChildElem in aElement.mChildren:
            self.generateHtml(aElement, xChildElem, aArgsList, aDictionary)

        if aElement.mTagName == 'cdata':
            xValue = aElement.mValue
            if xValue != None:
                try:
                    if isinstance(xValue, list):
                        pass      
                    if aArgsList:
                        xHtmlValues = [html.escape(x) for x in aArgsList]
                        xValue      = xValue.format(*xHtmlValues)
                    elif aDictionary:
                        xValue      = xValue.format(**aDictionary)
                except Exception as xEx:
                    pass
                aParent.mInnerHtml.write(xValue)
        else:
            
            if aDictionary:
                for xKey, xValue in aElement.items():
                    try:
                        aElement[xKey] = xValue.format(**aDictionary)
                    except KeyError:
                        pass

            if aElement.mTagName == 'area':
                pass
                    
            if aElement.get('class') == 'eezzTreeNode' and aElement.mJsonObj:
                # and aElement.mTagName == 'tr':
                try:                    
                    if aDictionary:
                        xTreeName  = aDictionary.get('name')
                        xTreeId    = aDictionary.get('table_id')
                        
                        if xTreeName and xTreeId:
                            xEvtUpdate = {'{}.innerHTML.{}'.format(xTreeName, xTreeId):'*'}
                            aElement.mJsonObj['update'] = xEvtUpdate
                            aElement['data-eezz-event'] = urllib.parse.quote( json.dumps(aElement.mJsonObj) )
                except KeyError as xEx:
                    pass
        
            aParent.mInnerHtml.write(aElement.generateHtml())            
        
# --------------------------------------------------------
# Main for test
# --------------------------------------------------------
if __name__ == '__main__':
    pass

