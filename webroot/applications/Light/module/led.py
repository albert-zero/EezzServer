'''
Created on 15.02.2016

'''

from   jaraco.video  import capture
from   eezz.service  import TBlackBoard
from   eezz.table    import TTable
import threading
import uuid


class TLight(): 
    def set_value_blue(self, intensity=0):
        print('blue ' + intensity)
    
    def set_value_red(self, intensity=0):
        print('blue ' + intensity)
    pass


