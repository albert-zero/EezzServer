# ---------------------------------------------------------------
#
# Test script to generate a master/detail view as directory/files
# ---------------------------------------------------------------
import os
from   eezz.table import TTable
from   eezz.table import TCell
from   sys import path
# from test.test_importlib.extension.util import PATH

# ---------------------------------------------------------------
# ---------------------------------------------------------------
class TDirView(TTable):
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def __init__(self, path='', node='', visible_items=80): 
        super().__init__(['directories'], 'directories')
        self.mCurrPath     = os.getcwd()
        self.mDetail       = TTable(['files'], 'files')
        self.mTreeRoot     = None
        self.mTreeSegm     = TTable(['directories'], 'directories')
        self.mPathStore    = dict()
        self.mVisibleItems = visible_items
        self.do_select()
        print ('TDirView')
        
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def do_select(self, index = -1):
        super().do_select(index)
        xSelectedDir = self.get_selected_row()
        
        if xSelectedDir:
            if xSelectedDir[1] == '..':
                xCurrPath = os.path.split(self.mHeaderDic['selected_entry'])[0]
            else:
                xCurrPath = os.path.join(self.mHeaderDic['selected_entry'], xSelectedDir[1])
        else:
            xCurrPath = os.getcwd()

        xWalk = next(os.walk(xCurrPath))
        self.mHeaderDic['selected_entry'] = xWalk[0]
            
        self.clear()
        self.append(['..'])
        for xFile in xWalk[1]:
            self.append([xFile])

        self.mDetail.clear()
        self.mDetail.mHeaderDic['selected_entry'] = self.mHeaderDic['selected_entry']
        for xFile in xWalk[2]:
            self.mDetail.append([xFile])

    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def get_selected_obj(self, index=-1, visible_items=None, visible_block=None):
        if int(index) == -1:
            super().get_selected_obj(index, visible_items, visible_block)
            return {'return':{'code':200, 'value': self}}
        else:
            self.mDetail.get_selected_obj(-1, visible_items, visible_block)
            xRow = self.mDetail.get_selected_row()
            return {'return':{'code':200, 'value': self.mDetail}}

    
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def getTreeRoot(self, path='', node='', visible_items = 50): 
        # self.mVisibleItems = visible_items
        if self.mTreeRoot == None:
            self.getDirlist(path, node)
        return {'return':{'code':200, 'value': self.mTreeRoot}}
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def showFile(self, path=''): 
        # self.mVisibleItems = visible_items
        #if self.mTreeRoot == None:
        #    self.getDirlist(path, node)
        self.mTreeRoot = TTable()
        return {'return':{'code':200, 'value': self.mTreeRoot}}
        
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def navigate(self, path, node, where):
        xPath = path.replace('\\', '/')        
        xTree = self.mPathStore.get(xPath)
        if xTree != None:
            xTree.do_navigate(where=where)
            self.mTreeRoot = xTree
            
    # ---------------------------------------------------------------
    # ---------------------------------------------------------------
    def getDirlist(self, path ='', node=''):
        xPath = path.replace('\\', '/')        
        xTree = self.mPathStore.get(xPath)
        
        if xTree != None:
            self.mTreeRoot = xTree
            # return {'return':{'code':200, 'value': xTree}}
        
        xTree = TTable(['directory'], 'content', visible_items=20)      
        xTree.mPath = xPath
        
        try:
            xWalk = next(os.walk(xPath))
        except StopIteration:
            return {'return':{'code':403, 'value': xPath}}
            
        self.mHeaderDic['selected_entry'] = xWalk[0]
        
        for xFile in xWalk[1]:
            xTblNode = TTable(list(), xFile)
            xCell    = TCell(0, 'directory', {'data-current-path': os.path.join(xWalk[0], xFile)})
            xTree.append([xTblNode], xCell)
        
        for xFile in xWalk[2]:
            xCell    = TCell(0, 'file', {'data-current-path': os.path.join(xWalk[0], xFile)})
            xTree.append([xFile], xCell)
        
        xTree.mHeaderDic['selected_entry'] = path
        xTree.mHeaderDic['table_id']       = node
        self.mPathStore[xPath] = xTree
        self.mTreeRoot         = xTree
        return {'return':{'code':200, 'value': xTree}}
        
# ---------------------------------------------------------------
# ---------------------------------------------------------------
if __name__ == '__main__':
    aDirView = TDirView()
    aDirView.printTable()
    
    aDirView.mDetail.printTable()
