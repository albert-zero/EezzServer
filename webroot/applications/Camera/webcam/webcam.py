'''
Created on 15.02.2016

@author: d025762
'''
import numpy as np
import cv2
from   optparse import OptionParser

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
        self.mCamera      = cv2.VideoCapture(0)
        self.mCookie      = uuid.uuid1()
        self.mBlackboard  = TBlackBoard()
        self.mBlackboard.addInterest(self.mCookie)
        self.mTable       = TTable()
        self.mName        = 'picture{}.jpg'
        self.mDict        = {'sourcefile':'picture1.jpg'}
        pass
    
    # --------------------------------------------------------
    # --------------------------------------------------------
    def read(self):
        return self.mCamera.read()

    # --------------------------------------------------------
    # --------------------------------------------------------
    def release(self):
        self.mCamera.release()
    
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

            xResult, xFrame = self.mCamera.read() 
            cv2.imwrite(xPicture, xFrame)
            
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

        self.mCamera.release()
        cv2.destroyAllWindows()
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
    # Parse command line options
    aOptParser = OptionParser()
    aOptParser.add_option("-s", "--snapshot",  dest="snapshotFile",  help="create a picture")
    aOptParser.add_option("-c", "--circle",    dest="circleFile",    help="find circle")
    
    (aOptions, aArgs) = aOptParser.parse_args() 
    xCamera = cv2.VideoCapture(0)

    if aOptions.snapshotFile:    
        xResult, xImage = xCamera.read() 
        cv2.imwrite(aOptions.snapshotFile, xImage)
    
        cv2.imshow('snapshot', xImage)
        cv2.waitKey()
    
    if aOptions.circleFile:
        cImage = cv2.imread(aOptions.circleFile, 1)
        gImage = cv2.cvtColor(cImage, cv2.COLOR_RGB2GRAY)
        
        aFaceCascade = cv2.CascadeClassifier('/Users/d025762/opencv/data/haarcascades/haarcascade_frontalface_default.xml')
        aEyeCascade  = cv2.CascadeClassifier('/Users/d025762/opencv/data/haarcascades/haarcascade_eye.xml')
        #xCircles = cv2.HoughCircles(xImage, cv2.HOUGH_GRADIENT, 1, 50, param1=50, param2=30, minRadius=50, maxRadius=100)
        #xCircles = np.uint16(np.around(xCircles))
        
        #cImage = cv2.cvtColor(xImage, cv2.COLOR_GRAY2RGB)
        #for i in xCircles[0,:]:
        #    cv2.circle(cImage, (i[0],i[1]),i[2],(0,255,0),1)
        #    
        xFaces = aFaceCascade.detectMultiScale(gImage, 1.3, 5)
        for (x,y,w,h) in xFaces:
            cv2.rectangle(cImage,(x,y),(x+w,y+h),(255,0,0),2)
            xRoiGray  = gImage[y:y+h, x:x+w]
            xRoiColor = cImage[y:y+h, x:x+w]
            
            xEyes = aEyeCascade.detectMultiScale(xRoiGray)
            for (ex,ey,ew,eh) in xEyes:
                cv2.rectangle(xRoiColor,(ex,ey),(ex+ew,ey+eh),(0,255,0),2)
    
        cv2.imshow('snapshot', cImage)
        cv2.waitKey()
    
    xCamera.release()
    cv2.destroyAllWindows()
    
    
