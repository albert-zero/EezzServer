# -*- coding: utf-8 -*-
# --------------------------------------------------------
# File  : bluethooth 
# Author: Abert Zedlitz
# Date  : 17.08.2013
# Description:
#      Defines bluethooth sercices
# ------------------------------------------------------
import threading

# --------------------------------------------------------
# --------------------------------------------------------
def singleton(aCls):
    aInstances = {}
    def getInstance():
        if aCls not in aInstances:
            aInstances[aCls] = aCls()
            aInstances[aCls].start()
        return aInstances[aCls]
    return getInstance

# --------------------------------------------------------
# --------------------------------------------------------
@singleton
class TBluetooth(threading.Thread):
    # --------------------------------------------------------
    # --------------------------------------------------------
    def __init__(self):
        super().__init__(name='bluetooth')
                                  
    # --------------------------------------------------------
    # --------------------------------------------------------
    def run(self):
        return
            


   