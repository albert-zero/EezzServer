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
import os
import http.server
import http.cookies
from   threading      import Thread
from   urllib.parse   import urlparse
from   urllib.parse   import parse_qs
from   optparse       import OptionParser
from   websocket      import TWebSocket
from   pathlib        import Path
from   http_agent     import THttpAgent
from   service        import TService
import time
import logging


class TWebServer(http.server.HTTPServer):
    """ WEB Server encapsulate the WEB socket implementation """
    def __init__(self, a_server_address, a_http_handler, a_web_socket):
        self.m_socket_inx  = 0
        self.m_server_addr = a_server_address
        self.m_web_addr    = (a_server_address[0], int(a_web_socket))
        self.m_web_socket  = TWebSocket(self.m_web_addr, THttpAgent)
        self.m_web_socket.start()
        super().__init__(a_server_address, a_http_handler)

    def shutdown(self):
        self.m_web_socket.shutdown()
        super().shutdown()


class THttpHandler(http.server.SimpleHTTPRequestHandler):
    """ HTTP handler for incoming requests """
    def __init__(self, request, client_address, server):
        self.m_client       = client_address
        self.m_server       = server
        self.m_request      = request
        self.server_version = 'eezzyServer/2.0'
        self.m_http_agent   = THttpAgent()
        super().__init__(request, client_address, server)
    
    def do_GET(self):
        """ handle GET request """
        self.handle_request()
        pass

    def do_POST(self):
        """ handle POST request """
        self.handle_request()

    def shutdown(self, args: int = 0):
        self.m_server.shutdown()

    def handle_request(self):
        """ handle GET and POST requests """
        x_cookie = http.cookies.SimpleCookie()

        if 'eezzAgent' not in x_cookie:
            x_cookie['eezzAgent'] = 'AgentName'

        x_morsal     = x_cookie['eezzAgent']
        x_result     = urlparse(self.path)
        x_query      = parse_qs(x_result.query)
        x_query_path = x_result.path

        if self.m_client[0] in ('localhost', '127.0.0.1'):
            if x_query_path == '/system/shutdown':
                xxx = Thread(target=shutdown_function, args=[self])
                xxx.start()
                # self.send_response(404)
                # self.end_headers()
                return
            if x_query_path == '/system/eezzyfree':
                pass

        x_resource = TService().root_path / f'public/.{x_query_path}'
        if x_resource.is_dir():
            x_resource = TService().root_path / 'public/index.html'

        if not x_resource.exists():
            self.send_response(404)
            self.end_headers()
            return

        if x_resource.suffix in '.html':
            x_result = self.m_http_agent.do_get(x_resource, x_query)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(x_result.encode('utf-8'))
        elif x_resource.suffix in ('.png', '.jpg', '.gif', '.mp4', '.ico'):
            self.send_response(200)
            self.send_header('content-type', 'image/{}'.format(x_resource.suffix)[1:])
            self.end_headers()
            with x_resource.open('rb') as f:
                self.wfile.write(f.read())
        elif x_resource.suffix in '.css':
            self.send_response(200)
            self.send_header('content-type', 'text/css')
            self.end_headers()
            with x_resource.open('rb') as f:
                self.wfile.write(f.read())


def shutdown_function(handler: THttpHandler):
    handler.shutdown(0)
    time.sleep(2)
    # os._exit(0)


if __name__ == "__main__":
    print(""" 
        EezzServer  Copyright (C) 2015  Albert Zedlitz
        This program comes with ABSOLUTELY NO WARRANTY;'.
        This is free software, and you are welcome to redistribute it
        under certain conditions;.
    """)

    # Parse command line options
    x_opt_parser = OptionParser()
    x_opt_parser.add_option("-d", "--host",      dest="http_host",  default="localhost", help="HTTP Hostname (for example localhost)")
    x_opt_parser.add_option("-p", "--port",      dest="http_port",  default="8000",      help="HTTP Port (default 8000")
    x_opt_parser.add_option("-w", "--webroot",   dest="web_root",   default="webroot",   help="Web-Root (path to webroot directory)")
    x_opt_parser.add_option("-x", "--websocket", dest="web_socket", default="8100",      help="Web-Socket Port (default 8100)",  type="int")
    x_opt_parser.add_option("-t", "--translate", dest="translate",  action="store_true", help="Optional creation of POT file")

    (x_options, x_args) = x_opt_parser.parse_args()
    x_service = TService(root_path=Path(x_options.web_root), host=x_options.http_host, websocket_addr=x_options.web_socket, translate=x_options.translate)

    if x_service.public_path.is_dir():
        os.chdir(x_service.public_path)
    else:
        x_opt_parser.print_help()
        logging.critical(f'webroot not found. Given path "{x_service.root_path}"\n'
                         f'terminating')
        exit(0)

    x_httpd   = TWebServer((x_options.http_host, int(x_options.http_port)), THttpHandler, x_options.web_socket)
    logging.info(f"serving {x_options.http_host} at port {x_options.http_port} ...")

    x_httpd.serve_forever()
    logging.info('shutdown')
    exit(os.EX_OK)
