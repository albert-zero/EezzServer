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
        