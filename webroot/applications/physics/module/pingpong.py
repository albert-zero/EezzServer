# -*- coding: utf-8 -*-
"""
    Copyright (C) 2015  Albert Zedlitz


"""
import time
import threading
from   eezz.service import TBlackBoard

class TObject(threading.Thread):
    # --------------------------------------------------------
    # --------------------------------------------------------
    def __init__(self):
        super().__init__(name='pingpong')
        self.mDict = dict()
        self.mDict['x']  = 0
        self.mDict['y']  = 0
        self.mDict['vx'] = 0
        self.mDict['vy'] = 0
                
    # --------------------------------------------------------
    # --------------------------------------------------------
    def start_object(self, x, y, vx, vy):
        self.mDict['x']  =  x
        self.mDict['y']  =  y
        self.mDict['vx'] = vx
        self.mDict['vy'] = vy
        return {'return':{'code':200, 'value': self}}

    # --------------------------------------------------------
    # --------------------------------------------------------
    def run(self):
        xCounter = 0
        
        while True:            
            time.sleep(1)
            
            
    # --------------------------------------------------------
    # --------------------------------------------------------
    def get_dictionary(self):
        return {'return': {'code':200, 'value': self.mDict}}


if __name__ == '__main__':
    pass