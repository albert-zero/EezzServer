'''
Created on 15.02.2016

@author: d025762
'''

from   jaraco.video  import capture
from   eezz.service  import TBlackBoard
from   eezz.table    import TTable
import threading
import uuid
import os
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
class TCamera(threading.Thread):
    # --------------------------------------------------------
    # --------------------------------------------------------
    def __init__(self):
        super().__init__(name='camera')

        self.mStopEvent   = threading.Event()
        self.mCamera      = capture.Device(devnum = 0)
        self.mCookie      = uuid.uuid1()
        self.mBlackboard  = TBlackBoard()
        self.mBlackboard.addInterest(self.mCookie)
        self.mTable       = TTable()
        self.mName        = 'picture{}.jpg'
        self.mDict        = {'sourcefile':'picture1.jpg'}
        pass
    
    # --------------------------------------------------------
    # --------------------------------------------------------
    def run(self):
        xCounter = 0
        
        while True:            
            xCounter += 1
            xPicture  = self.mName.format(xCounter)
            xInterest = self.mBlackboard.getInterest(self.mCookie)
            if xInterest and xInterest.get('sender') == 'system':
                if xInterest.get('system') == 'shutdown':
                    break

            self.mCamera.save_snapshot(xPicture, quality=95)
            if self.mStopEvent.wait(2):
                break
            self.mDict.update({'sourcefile':xPicture})    
            self.mBlackboard.addMesage(self.mCookie, 'camera')
            
            try:
                if xCounter >= 4:
                    xDelete = xCounter - 4
                    os.remove(self.mName.format(xDelete))
            except:
                pass

        pass
    # --------------------------------------------------------
    # --------------------------------------------------------
    def get_camera(self):
        return {'return':{'code':200, 'value': self}}
    
    # --------------------------------------------------------
    # --------------------------------------------------------
    def get_dictionary(self):
        return {'return': {'code':200, 'value': self.mDict}}


if __name__ == '__main__':
    xCam = capture.Device(devnum = 0)
    xCam.save_snapshot('test.jpg', quality=95)
    
    pass