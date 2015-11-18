# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# File  : easy.server
# Author: Albert Zedlitz
#
# Description:
#   EEZZyServer runs an HTTP server, which utilizes EEZZyAgent to process the HTML input
#   
# ----------------------------------------------------------------------------

import os, copy
import cgi
import http.server, urllib.parse
import http.cookies
from   urllib.parse   import urlparse
from   urllib.parse   import parse_qs
import json

from   optparse       import OptionParser
from   websocket      import TWebSocket
from   agent          import TEezzAgent
import xml.etree.ElementTree
import urllib.request
from   blueserv import TBluetooth

# Class THttpHandler
#    HTTP Handler for incoming requests 
# ---------------------------------    
class TWebServer(http.server.HTTPServer):
    def __init__(self, aServerAddress, aHttpHandler, aWebSocket):
        print('Initialize TWebServer ...')
        self.mSocketInx  = 0
        self.mServerAddr = aServerAddress
        self.mWebAddr    = (aServerAddress[0], int(aWebSocket))
        self.mWebSocket  = TWebSocket(self.mWebAddr)
        self.mWebSocket.start()
        self.mRunning    = True
        self.mBluetooth  = TBluetooth()
        
        # start the user services
        # aAgent           = TEezzAgent()
        # aAgent.startServices()
        super().__init__(aServerAddress, aHttpHandler)
        
    # ---------------------------------    
    def serve_forever(self):
        while self.mRunning:
            self.handle_request()
   
    # ---------------------------------    
    def shutdown(self):
        self.mWebSocket.shutdown()
        self.mRunning = False

# Class THttpHandler
#    HTTP Handler for incoming requests 
# ---------------------------------    
class THttpHandler(http.server.SimpleHTTPRequestHandler):   
    def __init__(self, request, client_address, server):
        self.mClient = client_address
        self.mServer = server
        self.server_version = 'eezzyServer/1.0'
        super().__init__(request, client_address, server)     
    
    # Handle a GET request
    # Returns the index.htlm
    # ---------------------------------    
    def do_GET(self):      
        aEnv   = copy.deepcopy(os.environ)  
        aEnv['REQUEST_METHOD'] = 'GET'
        
        aForm = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=aEnv)        
        self.doHandleRequest(aForm)
            
    # Handle a POST request
    # Reads the commands and returns a mixed-in index.html
    # ---------------------------------    
    def do_POST(self):
        aEnv   = copy.deepcopy(os.environ)  
        aEnv['REQUEST_METHOD'] = 'POST'
        aEnv['CONTENT_TYPE']   = self.headers['Content-Type']
    
        aForm = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=aEnv)
        self.doHandleRequest(aForm)        
        

    # ---------------------------------    
    def doHandleRequest(self, aForm):
        aCookie = http.cookies.SimpleCookie()
        
        if 'Cookie' in aForm.headers:     
            xValue = aForm.headers.get('Cookie')
            aCookie.load(xValue)
            
        if 'eezzAgent' not in aCookie:
            aCookie['eezzAgent'] = 'AgentName'

        xMorsal   = aCookie['eezzAgent']
        xResult   = urlparse(self.path)
        xQuery    = parse_qs(xResult.query)
        xRelPath  = xResult.path.replace('/', os.sep)
        
        if xRelPath == os.sep:
            xRelPath = os.path.join('.', self.path[1:], 'index.html')
        else:
            if self.mClient[0] in ('localhost', '127.0.0.1'):
                try:
                    if xResult.path == '/service/eezzyfree':
                        xAgent    = TEezzAgent(self.server.mServerAddr, self.server.mWebAddr)
                        xResponse = xAgent.service('bluetooth', 'GETUSR')
                        
                        xJsonStr  = json.dumps(xResponse)
                        self.wfile.write(xJsonStr.encode('utf8'))
                        return
                    
                    if xResult.path == '/service/eezzylock':
                        xAgent    = TEezzAgent(self.server.mServerAddr, self.server.mWebAddr)
                        xResponse = xAgent.service('bluetooth', 'LOCKWS')

                        xJsonStr  = json.dumps(xResponse)
                        self.wfile.write(xJsonStr.encode('utf8'))
                        return
                    
                    if xResult.path == '/service/system' and 'exit' in xResult.query:
                        xAgent    = TEezzAgent(self.server.mServerAddr, self.server.mWebAddr)
                        xResponse = xAgent.service('system', 'shutdown')

                        xJsonStr  = json.dumps(xResponse)
                        self.wfile.write(xJsonStr.encode('utf8'))
                                                
                        self.mServer.shutdown()
                        return
                except ConnectionResetError:
                    pass
        
        xPath, xFile = os.path.split(xRelPath)
        xBase, xExt  = os.path.splitext(xFile)
                
        xResource = os.path.join('.', xRelPath[1:])
        
        try:
            if xExt == '.html':
                xAgent = TEezzAgent(self.server.mServerAddr, self.server.mWebAddr)
                
                if xQuery:
                    xResponse = xAgent.handle_request(xRelPath, aForm, False, {'arguments':xQuery})
                else:    
                    xResponse = xAgent.handle_request(xRelPath, aForm)
                xAgent.shutdown()
                # xResponse = xResponse['return']['value']
    
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                
                xKey, xValue = str(aCookie).split(':',1)
                self.send_header(xKey, xValue)  
                
                self.end_headers() 
                self.wfile.write( xResponse.encode('utf-8') )
                      
            elif xExt in ('.png', '.jpg', '.gif', '.mp4', '.ico'):
                self.send_response(200)
                self.send_header('content-type', 'image/{}'.format(xExt[1:]))
                self.end_headers()

                with open(xResource, 'rb') as xSource:
                    self.wfile.write( xSource.read() )

            elif xExt in ('.css'):
                self.send_response(200)
                self.send_header('content-type', 'text/css')
                self.end_headers()
                
                with open(xResource, 'rb') as xSource:
                    self.wfile.write( xSource.read() )
                    
            elif xExt in ('.avi', '.mp4'):
                self.send_response(200)
                self.send_header('content-type', 'video/mp4')
                self.end_headers()
                
                with open(xResource, 'rb') as xSource:
                    self.wfile.write( xSource.read() )
            
            elif xExt in ('.odt',):
                self.send_response(200)
                self.send_header('content-type', 'application/vnd.oasis.opendocument.text')
                self.end_headers()
                
                with open(xResource, 'rb') as xSource:
                    self.wfile.write( xSource.read() )
            
            else:
                if os.path.exists(xResource):
                    with open(xResource, 'rb') as xSource:
                        self.wfile.write( xSource.read() )
                else:
                    self.send_response(403)
                    self.end_headers()
        
        except ValueError as xEx:
            raise           
        except Exception as xEx:
            self.send_response(403)
            self.end_headers()
            # raise xEx
            # self.wfile.write( str(xEx) )
            
                            
        
# Main loop
#    Defines the option parser
#    Creates the client thread
#    Creates the agent thread
#    Starts the HTTP server
# ---------------------------------
import sys    

if __name__ == "__main__":
    # Parse command line options
    aOptParser = OptionParser()
    aOptParser.add_option("-d", "--host",      dest="aHttpHost",   default="localhost", help="HTTP Hostname")
    aOptParser.add_option("-p", "--port",      dest="aHttpPort",   default="8000",      help="HTTP Port")
    aOptParser.add_option("-w", "--webroot",   dest="aWebRoot",    default="webroot",   help="Web-Root")
    aOptParser.add_option("-x", "--websocket", dest="aWebSocket",  default="8100",      help="Web-Socket Port")
    
    (aOptions, aArgs) = aOptParser.parse_args() 
    xPath = os.path.join(aOptions.aWebRoot.replace('/', os.path.sep), 'public')
    
    if os.path.isdir(xPath):
        os.chdir(xPath)
    else:
        print('web root not found: {}'.format(xPath))
        os._exit(0)
        
    aHttpd  = TWebServer((aOptions.aHttpHost, int(aOptions.aHttpPort)), THttpHandler, aOptions.aWebSocket)
           
    # Start the HTTP server
    print("serving {0} at port {1} ...".format(aOptions.aHttpHost, aOptions.aHttpPort))    
    aHttpd.serve_forever()
    print('shutdown')

    