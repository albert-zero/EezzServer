# -*- coding: utf-8 -*-
# --------------------------------------------------------
# File  : service
# Author: Abert Zedlitz
# Date  : 17.08.2013
# Description:
#      Blackboard for data exchange of services
# ------------------------------------------------------

# --------------------------------------------------------
# --------------------------------------------------------
def singleton(aCls):
    aInstances = {}
    def getInstance():
        if aCls not in aInstances:
            aInstances[aCls] = aCls()
        return aInstances[aCls]
    return getInstance

# --------------------------------------------------------
# --------------------------------------------------------
@singleton
class TBlackBoard:
    # --------------------------------------------------------
    # --------------------------------------------------------
    def __init__(self):
        self.mBlackBoard  = dict()
    
    def addMesage(self, aName, aData):
        for xInterest in self.mBlackBoard.values():
            xInterest[aName] = aData
    
    def addInterest(self, aCookie):
        if not self.mBlackBoard.get(aCookie):
            self.mBlackBoard[aCookie] = dict()
    
    def delInterest(self, aCookie):
        if self.mBlackBoard.get(aCookie):
            del self.mBlackBoard[aCookie]

    def getInterest(self, aCookie):
        if self.mBlackBoard.get(aCookie):
            xInterest = self.mBlackBoard[aCookie]
            self.mBlackBoard[aCookie] = dict()
            return xInterest
        