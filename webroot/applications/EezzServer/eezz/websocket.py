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

Description:
   Implements websocket protocol according to rfc 6455 
   https://tools.ietf.org/html/rfc6455
 
"""
import io, socket, struct
from   Crypto.Hash import SHA
import base64
import select
import json
import threading
from   agent import TEezzAgent
  
# Define exception
# ----------------------------------------------------------------
class TWebSocketException(Exception):
    def __init__(self, aValue):
        self.value = aValue
    def __str__(self):
        return repr(self.value)

# ----------------------------------------------------------------
# Define a client web socket handler
# ----------------------------------------------------------------
class TWebSocketClient():
    # Initialize Thread
    # --------------------------------------------------------
    def __init__(self, xCltAddr, xWebAddr):
        self.mSocket  = xCltAddr[0]
        self.mState   = 0
        self.mAddress = xWebAddr
        self.mAgent   = None
        self.mCnt     = 0
        self.mBuffer  = None
        self.mLock    = threading.Lock()
        
    # --------------------------------------------------------             
    # thread main method
    # --------------------------------------------------------
    def doInput(self):
        if self.mState == -1:
            raise TWebSocketException('input: connection closed');
        xFinal, xOpcode, xMaskVector, xPayloadLen = (False,0,0,0)
        
        try:
            if self.mState == 0:
                self.mState = 1
                xBinData   = self.mSocket.recv(1024)
                
                print('connect...')
                if len(xBinData) == 0:
                    raise TWebSocketException('no data received')
                
                xData        = xBinData.decode('utf-8')        
                xResponse    = self.genHandshake(xData)    
                xNrBytes     = self.mSocket.send(xResponse.encode('utf-8'))
                self.mAgent  = TEezzAgent(None, self.mAddress, self)
                self.mBuffer = bytearray(65536*2)
                return None
            
            xFinal = False
            while not xFinal:
                xFinal, xOpcode, xMaskVector, xPayloadLen = self.readHeader()
                
                if xOpcode == 0x8:
                    raise TWebSocketException("closed connection")
                elif xOpcode == 0x1:
                    xJsonStr = self.readFrame(xOpcode, xMaskVector, xPayloadLen)
                    xJsonObj = json.loads(xJsonStr[:xPayloadLen].decode('utf-8'))

                    if 'file' in xJsonObj:
                        xStream   = self.doInput()
                        xJsonResp = self.mAgent.handle_download(xJsonObj, xStream)                            
                        self.writeFrame(json.dumps(xJsonResp).encode('utf-8'))
                        return
                    
                    aResponse = self.mAgent.handle_websocket(xJsonObj)                        
                    if aResponse != None:
                        self.writeFrame(aResponse.encode('utf-8'))
                        
                elif xOpcode == 0x2:
                    return self.readFrame(xOpcode, xMaskVector, xPayloadLen) 
                elif xOpcode == 0x9:
                    xData = self.readFrame(xOpcode, xMaskVector, xPayloadLen)
                    self.writeFrame(aData=xData[:xPayloadLen], aOpCode=0xA, aFinal=(1<<7), aMaskVector = None)
                else:
                    raise TWebSocketException("unknown opcode={}".format(xOpcode))         
        except Exception as xEx:
            if self.mAgent:
                print("communication: connection closed: " + str(xEx))
                self.mAgent.shutdown()
            self.mState = -1;
            raise
        return None
        
    # --------------------------------------------------------
    # --------------------------------------------------------
    def doUpdate(self, aJsonObj):
        if self.mState == -1:
            raise TWebSocketException('update: connection closed');

        aResponse = self.mAgent.handle_websocket(aJsonObj, False)
        if aResponse != None:
            try:
                self.writeFrame(aResponse.encode('utf-8'))                 
            except:
                self.mState = -1;
                raise
                        
    # --------------------------------------------------------
    # Define the handshake
    # --------------------------------------------------------
    def genHandshake(self, aData):
        xLines        = aData.splitlines()
        self.mHeaders = dict([ x.split(':', 1) for x in xLines[1:] if ':' in x])
        
        try:
            xKey          = self.genKey()
        except:
            pass
        
        with io.StringIO() as xHandshake:
            xHandshake.write('HTTP/1.1 101 Switching Protocols\r\n')
            xHandshake.write('Connection: Upgrade\r\n')
            xHandshake.write('Upgrade: websocket\r\n')
            xHandshake.write('Sec-WebSocket-Accept: {}\r\n'.format(xKey))
            xHandshake.write('\r\n')
            aResult = xHandshake.getvalue() 
        
        return aResult 
    
    # --------------------------------------------------------
    # Generate key for Sec-WebSocket-Accept
    # --------------------------------------------------------
    def genKey(self):
        xhash     = SHA.new()
        x64Key    = self.mHeaders.get('Sec-WebSocket-Key').strip()
        xKey      = x64Key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        xhash.update(bytes(xKey, 'ascii'))
        return base64.b64encode(xhash.digest()).decode('utf-8')    

    # --------------------------------------------------------
    # Read a single frame
    # --------------------------------------------------------
    def readHeader(self):
        xBytes      = self.mSocket.recv(2)
        
        if len(xBytes) == 0:
            raise TWebSocketException('no data received')
                
        xMaskVector = None
        xFinal      = ((1<<7) & xBytes[0]) != 0 
        xOpcode     = xBytes[0] & 0xf

        xMasked     = ((1<<7) & xBytes[1]) != 0
        xPayloadLen = int( xBytes[1] & 0x7f )        

        # calculate extended length
        if xPayloadLen == 126:
            xBytes = self.mSocket.recv(2)
            xPayloadLen = struct.unpack('>H', xBytes)[0]
        elif xPayloadLen == 127:
            xBytes = self.mSocket.recv(8)
            xPayloadLen = struct.unpack('>Q', xBytes)[0]

        # unpack data
        if xMasked:
            xMaskVector = self.mSocket.recv(4) 
        
        return (xFinal, xOpcode, xMaskVector, xPayloadLen)
        

    # --------------------------------------------------------
    # Read a single frame
    # --------------------------------------------------------
    def readFrame(self, xOpcode, xMaskVector, xPayloadLen):
        if xPayloadLen == 0:
            return str()
        
        xRest   = xPayloadLen 
        xView   = memoryview(self.mBuffer)
        
        while xRest > 0:
            xNumBytes = self.mSocket.recv_into(xView, xRest)
            xRest     = xRest - xNumBytes
            xView     = xView[xNumBytes:]
                    
        if xMaskVector:
            xDimension  = divmod((xPayloadLen + 3), 4)
            xView       = memoryview(self.mBuffer)
            
            xIntSize    = xDimension[0]                
            xSeqMask    = struct.unpack('>I', bytearray(reversed(xMaskVector)))[0]
            xViewSli    = xView[: xIntSize * 4]
            xViewInt    = xViewSli.cast('I')
            
            # Calculate un-mask with int4
            for i in range(xIntSize):
                xViewInt[i] ^= xSeqMask

            xViewInt.release()
            xViewSli.release()
                                
        return self.mBuffer

    # --------------------------------------------------------
    # Write a single frame
    # --------------------------------------------------------
    def writeFrame(self, aData, aOpCode=0x1, aFinal=(1<<7), aMaskVector = None):
        with self.mLock:
            xPayloadLen  = len(aData)
            xBytes       = bytearray(10)
            xPos         = 0
            xMasked      = 0x0
            
            if aMaskVector != None and len(aMaskVector) == 4:
                xMasked = 1<<7
                
            xBytes[xPos] = aFinal | aOpCode 
            xPos        += 1
            
            if xPayloadLen > 126:
                if xPayloadLen < 0xffff:
                    xBytes[xPos]  = 0x7E | xMasked
                    xPos += 1
                    xBytes[xPos:xPos+2] = struct.pack('>H', xPayloadLen)
                    xPos += 2
                else:
                    xBytes[xPos]  = 0x7F | xMasked
                    xPos += 1
                    xBytes[xPos:xPos+8] = struct.pack('>Q', xPayloadLen)
                    xPos += 8
            else:
                xBytes[xPos] = (xPayloadLen) | xMasked
                xPos += 1
            
            self.mSocket.send(xBytes[0:xPos])
            if xPayloadLen == 0:
                return
            
            if xMasked != 0:
                xMasked = bytearray(xPayloadLen)
                
                for i in range(xPayloadLen):
                    xMasked[i] = ord(aData [i]) ^ aMaskVector[i % 4]
                self.mSocket.send(xMasked)
            else:
                self.mSocket.sendall(aData)
        
# ------------------------------------------------------------
# Manage the web socket port
# ------------------------------------------------------------
class TWebSocket(threading.Thread):
    mWebClient = None
    
    # Initialize
    # --------------------------------------------------------
    def __init__(self, aWebAddress):
        self.mWebAddr         = aWebAddress
        self.mClients         = dict()
        self.mRunning         = True
        self.mWebSocketServer = None
        super().__init__()
        
    # --------------------------------------------------------
    # --------------------------------------------------------
    def shutdown(self):
        self.mRunning = False
        self.mWebSocketServer.close()
    
    # Wait for incoming connection requests         
    # --------------------------------------------------------
    def run(self):   
        self.mWebSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mWebSocketServer.bind(self.mWebAddr)
        self.mWebSocketServer.listen(15)
        aReadList  = [self.mWebSocketServer]
        
        # aWebSocket.settimeout(60)
        print('websocket {} at {}'.format(self.mWebAddr[0], self.mWebAddr[1]))

        while self.mRunning:
            xRd, xWr, xErr = select.select(aReadList, [], aReadList)
            
            for xSocket in xErr:
                if xSocket is self.mWebSocketServer:
                    xSocket.close()
                    aReadList.remove(xSocket)                    
                    print('server socket closed')
                    raise
                else:
                    self.mWebClient = None
                    xSocket.close()
                    aReadList.remove(xSocket)                    
                    self.mClients.pop(xSocket)
                pass
            
            for xSocket in xRd:
                if xSocket is self.mWebSocketServer:
                    try:
                        xCltAddr = self.mWebSocketServer.accept()
                        self.mClients[xCltAddr[0]] = TWebSocketClient(xCltAddr, self.mWebAddr)
                        aReadList.append(xCltAddr[0])
                    except:
                        break
                else:
                    try:
                        self.mClients.get(xSocket).doInput()
                    except (TWebSocketException, ConnectionResetError, ConnectionAbortedError) as aEx:
                        xSocket.close()
                        aReadList.remove(xSocket)
                        self.mClients.pop(xSocket)

