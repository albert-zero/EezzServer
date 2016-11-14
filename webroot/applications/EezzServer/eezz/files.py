# -*- coding: utf-8 -*-
"""
    Copyright (C) 2015 www.EEZZ.biz (haftungsbeschränkt)

    TFileWriter
    Manages download of one files in slices
    
    TFileDownloader
    Manages download of a set of files

"""
import uuid
import os
import threading
import mmap
import base64
import json, math
import re
from   Crypto.Hash      import SHA256


# -------------------------------------------------------------
# Download manager
# Encrypt data and create hash codes
# -------------------------------------------------------------
class TFileWriter():
    # -------------------------------------------------------------
    # -------------------------------------------------------------    
    def __init__(self, aHeader, aChunkSize, aFilePath):
        
        self.mName       = aFilePath
        self.mSize       = int( aHeader['size'] )
        self.mFileType   = aHeader['type']
        self.mTransfered = 0
        self.mAvailable  = dict()
        self.mSequence   = 0
        self.mChunk      = 0
        self.mChunkSize  = aChunkSize
        self.mNumChunks  = divmod(self.mSize, self.mChunkSize)[0] + 1
        self.mWork       = threading.Condition()
        self.mAccess     = threading.Lock()
        self.mLock       = threading.Lock()
        self.mHash       = SHA256.new()
        
        xSize = self.mSize        
        with open(self.mName, "w+b") as fout:
            fout.seek(max(0, xSize - 1))
            fout.write(b'\x00')
                    
        self.mEncHash = [0 for x in range(self.mNumChunks)]
        
    # -------------------------------------------------------------
    # -------------------------------------------------------------    
    def reset(self):
        self.mAvailable.clear()
        self.mTransfered = 0
        self.mSequence   = 0

    # -------------------------------------------------------------
    # -------------------------------------------------------------    
    def getLoad(self):
        return math.floor(100 * (self.mTransfered+1)/(self.mSize+1))

    # -------------------------------------------------------------
    # -------------------------------------------------------------    
    def checkReady(self):
        return self.mTransfered >= self.mSize
    
    # -------------------------------------------------------------
    # Download a file in chunks and calculate a hash 
    # -------------------------------------------------------------    
    def writeChunk(self, aHeader, aStream):
        xHash = SHA256.new()
                        
        with open(self.mName, "r+b") as fout:
            # Accept any chunk any time
            xSeqSize   = int(aHeader['chunkSize'])
            xSeqNr     = int(aHeader['sequence'])
            xSeqStart  = int(aHeader['start'])
            
            self.mTransfered  += xSeqSize
                        
            xStream    = aStream[:xSeqSize]
            xStart     = xSeqStart
            xEnd       = xStart + xSeqSize
                        
            xMemMap     = mmap.mmap(fout.fileno(), 0)
            xViewMem    = memoryview(xMemMap)
            xViewSli    = xViewMem[xStart : xEnd]
            xViewSli[:] = xStream
            
            xViewSli.release()
            xViewMem.release()
            xMemMap.close()

            xHash.update(xStream)
            self.mEncHash[xSeqNr] = base64.b64encode(xHash.digest()).decode('utf-8')
            print("compile {}".format(xSeqNr))
    

        xDigest = base64.b64encode(xHash.digest())
        return xDigest.decode('utf-8')
       
# -------------------------------------------------------------
# Download a file
# After each chunk the load state 101 is returned with load 
# After the last chunk the return state 201 is returned 
# -------------------------------------------------------------
class TFileDownloader:
    # -------------------------------------------------------------    
    # -------------------------------------------------------------
    def __init__(self, filename = None):        
        self.mFileMap      = dict() 
        self.mValues       = dict()
        self.mChunkSize    = 0
        self.mFilename     = str()
        self.mTransId      = None
        self.mDocumentId   = 'testproj'
        self.mFrobidden    = re.compile(r'[^a-zA-Z0-9/_]')
        self.mValues       = dict()
        
    # -------------------------------------------------------------
    # Callback from user interface: Collect all files
    # -------------------------------------------------------------
    def readFiles(self, aHeader, aStream):        
        # first call with list of files
        if 'files' in aHeader:
            try:
                if not self.mFrobidden.search(aHeader['doc_root']):
                    self.mDocumentId = aHeader['doc_root']
            except KeyError:
                pass
            
            os.makedirs(os.path.join('documents', self.mDocumentId), exist_ok=True)
            
            for xFileWriter in self.mFileMap.values():
                if not xFileWriter.checkReady():
                    return {"return":{"code":420, "value":"download in progress"}, "progress":0}

            self.mCounter   = 0
            self.mChunkSize = int( aHeader['chunkSize'] )

            for xFileWriter in self.mFileMap.values():
                xFileWriter.reset()        
            
            return {"return":{"code":101, "value":"ready for download"}, "progress":0}
        
        if not 'file' in aHeader:
            return {"return":{"code":500, "value":"Not files found"}, "progress":0}
        
        # subsequent calls for each file in slices
        xFile       = aHeader['file']   
        xFileWriter = self.mFileMap.get(xFile['name'])
        
        # Create loader if not existing
        if xFileWriter == None:
            xDocDir = os.path.join('documents', self.mDocumentId)
            os.makedirs(xDocDir, exist_ok=True)
    
            xFileWriter = TFileWriter(xFile, self.mChunkSize, os.path.join('documents', self.mDocumentId, xFile['name']))
            self.mFileMap[xFile['name']] = xFileWriter
            
        xFileWriter.writeChunk( xFile, aStream )

        for xLoader in self.mFileMap.values():
            if not xLoader.checkReady():
                xCurrProgress = xFileWriter.getLoad()
                return {"return":{"code":101, "value":"ready for download"}, "progress": xCurrProgress}
                        
        self.mFileMap.clear()
        return {"return":{"code":201, "value":"finished"}, "progress": 100}
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def get_dictionary(self): 
        return {'return':{'code':200, 'value':self.mValues}};
    
# -------------------------------------------------------------
# -------------------------------------------------------------
if __name__ == '__main__':     
    exit()

 
