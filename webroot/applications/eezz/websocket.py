"""
    EezzServer: 
    High speed application development and 
    high speed execution based on HTML5
    
    Copyright (C) 2015  Albert Zedlitz

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
-
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
from   abc import abstractmethod
from   threading import Condition
import io
import struct
import socket
# from   Crypto.Hash import SHA
import hashlib
import base64
import select
import json
import threading
from enum   import Enum
from typing import Any, Callable


class TWebSocketAgent:
    """ User should implement this class to receive data """
    def __init__(self):
        pass

    @abstractmethod
    def handle_request(self, request_data: Any) -> str:
        """ handle request expects a json structure """
        return ''

    @abstractmethod
    def handle_download(self, description: str, raw_data: Any) -> str:
        """ handle download expects a json structure, describing the file and the data """
        return ''

    def shutdown(self):
        """ Implement shutdown to release allocated resources """
        pass


class TWebSocketException(Exception):
    """ Exception class for this module """
    def __init__(self, a_value):
        self.m_value = a_value

    def __str__(self):
        return repr(self.m_value)


class TWebSocketClient:
    """ Implements a WEB socket service thread """
    def __init__(self, a_client_addr: tuple, a_web_addr: int, a_agent: type[TWebSocketAgent]):
        self.m_headers      = None
        self.m_socket       = a_client_addr[0]
        self.m_address      = a_web_addr
        self.m_cnt          = 0
        self.m_buffer       = None
        self.m_protocol     = str()
        self.m_agent_class  = a_agent
        self.m_agent_client = None
        self.m_condition    = Condition()
        self.m_async        = TWebAsyncManager(self.handle_async_request, self.m_condition)
        self.m_async_req    = list()

        self.upgrade()
        self.m_async.start()

    def shutdown(self):
        self.m_async.shutdown()

    def upgrade(self):
        """ Upgrade HTTP connection to WEB socket """
        x_bin_data = self.m_socket.recv(1024)
        if len(x_bin_data) == 0:
            raise TWebSocketException('no data received')

        x_utf_data = x_bin_data.decode('utf-8')
        x_response = self.gen_handshake(x_utf_data)
        x_nr_bytes = self.m_socket.send(x_response.encode('utf-8'))
        self.m_agent_client = self.m_agent_class()
        self.m_buffer = bytearray(65536 * 2)

    def handle_async_request(self):
        for x in self.m_async_req:
            x_response = self.m_agent_client.handle_request(x)
            self.write_frame(x_response.encode('utf-8'))

    def handle_request(self) -> None:
        """ Receives an request and send a response """
        x_json_str = self.read_websocket()
        x_json_obj = json.loads(x_json_str.decode('utf-8'))

        if 'file' in x_json_obj:
            x_byte_stream = self.read_websocket()
            x_response    = self.m_agent_client.handle_download(x_json_obj, x_byte_stream)
        elif 'async' in x_json_obj:
            self.m_async_req.append(x_json_obj)
            return
        else:
            x_response    = self.m_agent_client.handle_request(x_json_obj)
        self.write_frame(x_response.encode('utf-8'))

    def read_websocket(self) -> bytes:
        try:
            x_raw_data = bytes()
            while True:
                x_final, x_opcode, x_mask_vector, x_payload_len = self.read_frame_header()
                if x_opcode == 0x8:
                    raise TWebSocketException("closed connection")
                elif x_opcode == 0x1:
                    x_raw_data += self.read_frame(x_opcode, x_mask_vector, x_payload_len)
                elif x_opcode == 0x2:
                    x_raw_data += self.read_frame(x_opcode, x_mask_vector, x_payload_len)
                elif x_opcode == 0x9:
                    x_utf_data = self.read_frame(x_opcode, x_mask_vector, x_payload_len)
                    self.write_frame(a_data=x_utf_data[:x_payload_len], a_opcode=0xA, a_final=(1 << 7))
                elif x_opcode == 0xA:
                    x_utf_data = self.read_frame(x_opcode, x_mask_vector, x_payload_len)
                    self.write_frame(a_data=x_utf_data[:x_payload_len], a_opcode=0x9, a_final=(1 << 7))
                else:
                    raise TWebSocketException(f"unknown opcode={x_opcode}")

                if x_final:
                    return x_raw_data
        except Exception as xEx:
            if self.m_agent_client:
                print("communication: connection closed: " + str(xEx))
                self.m_agent_client.shutdown()
                self.m_agent_client = None
            raise

    def gen_handshake(self, a_data: str):
        x_key           = 'accept'
        x_lines         = a_data.splitlines()
        self.m_headers  = {x_key: x_val for x_key, x_val in [x.split(':', 1) for x in x_lines[1:] if ':' in x]}
        self.m_protocol = self.m_headers.get('Upgrade')
        
        if self.m_protocol != 'peezz':
            x_key = self.gen_key()

        with io.StringIO() as x_handshake:
            x_handshake.write('HTTP/1.1 101 Switching Protocols\r\n')
            x_handshake.write('Connection: Upgrade\r\n')
            x_handshake.write('Upgrade: websocket\r\n')
            x_handshake.write('Sec-WebSocket-Accept: {}\r\n'.format(x_key))
            x_handshake.write('\r\n')
            x_result = x_handshake.getvalue()
        return x_result
    
    def gen_key(self):
        x_hash     = hashlib.sha1()
        x_64key    = self.m_headers.get('Sec-WebSocket-Key').strip()
        x_key      = x_64key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        x_hash.update(bytes(x_key, 'ascii'))
        return base64.b64encode(x_hash.digest()).decode('utf-8')

    def read_frame_header(self):
        x_bytes = self.m_socket.recv(2)
        
        if len(x_bytes) == 0:
            raise TWebSocketException('no data received')
                
        x_mask_vector = None
        x_final       = ((1 << 7) & x_bytes[0]) != 0
        x_opcode      = x_bytes[0] & 0xf
        x_masked      = ((1 << 7) & x_bytes[1]) != 0
        x_payload_len = int(x_bytes[1] & 0x7f)

        # calculate extended length
        if x_payload_len == 126:
            x_bytes = self.m_socket.recv(2)
            x_payload_len = struct.unpack('>H', x_bytes)[0]
        elif x_payload_len == 127:
            x_bytes = self.m_socket.recv(8)
            x_payload_len = struct.unpack('>Q', x_bytes)[0]

        # unpack data
        if x_masked:
            x_mask_vector = self.m_socket.recv(4)
        return x_final, x_opcode, x_mask_vector, x_payload_len

    def read_frame(self, x_opcode, a_mask_vector, a_payload_len):
        """ Read one frame """
        if a_payload_len == 0:
            return bytearray()
        
        x_rest   = a_payload_len
        x_view   = memoryview(self.m_buffer)
        
        while x_rest > 0:
            x_num_bytes = self.m_socket.recv_into(x_view, x_rest)
            x_rest     = x_rest - x_num_bytes
            x_view     = x_view[x_num_bytes:]
                    
        if a_mask_vector:
            x_dimension = divmod((a_payload_len + 3), 4)
            x_view      = memoryview(self.m_buffer)
            
            x_int_size  = x_dimension[0]
            x_seq_mask  = struct.unpack('>I', bytearray(reversed(a_mask_vector)))[0]
            x_view_sli  = x_view[: x_int_size * 4]
            x_view_int  = x_view_sli.cast('I')
            
            # Calculate un-mask with int4
            for i in range(x_int_size):
                x_view_int[i] ^= x_seq_mask

            x_view_int.release()
            x_view_sli.release()
                                
        return self.m_buffer[:a_payload_len]

    def write_frame(self, a_data: bytes, a_opcode: hex = 0x1, a_final: hex = (1 << 7), a_mask_vector: list = None) -> None:
        """ Write single frame """
        x_payload_len = len(a_data)
        x_bytes       = bytearray(10)
        x_position    = 0
        x_masked      = 0x0

        if a_mask_vector and len(a_mask_vector) == 4:
            x_masked = 1 << 7

        x_bytes[x_position] = a_final | a_opcode
        x_position         += 1

        if x_payload_len > 126:
            if x_payload_len < 0xffff:
                x_bytes[x_position]  = 0x7E | x_masked
                x_position += 1
                x_bytes[x_position:x_position+2] = struct.pack('>H', x_payload_len)
                x_position += 2
            else:
                x_bytes[x_position]  = 0x7F | x_masked
                x_position += 1
                x_bytes[x_position:x_position+8] = struct.pack('>Q', x_payload_len)
                x_position += 8
        else:
            x_bytes[x_position] = x_payload_len | x_masked
            x_position += 1

        if x_masked:
            x_bytes[x_position:x_position+4] = a_mask_vector
            x_position += 4

        self.m_socket.send(x_bytes[0:x_position])
        if x_payload_len == 0:
            return

        if x_masked != 0:
            x_masked = bytearray(x_payload_len)

            for i in range(x_payload_len):
                x_masked[i] = a_data[i] ^ a_mask_vector[i % 4]
            self.m_socket.send(x_masked)
        else:
            self.m_socket.sendall(a_data)


class TWebSocket(threading.Thread):
    """ Manage connections to the WEB socket interface """
    def __init__(self, a_web_address, a_agent_class: type[TWebSocketAgent]):
        self.m_web_socket: socket = None
        self.m_web_addr    = a_web_address
        self.m_clients     = dict()
        self.m_agent_class = a_agent_class
        self.m_running     = True
        super().__init__()
    
    def shutdown(self):
        """ Shutdown closes all sockets """
        self.m_running = False
        for x_key, x_val in self.m_clients.items():
            x_key.close()
        self.m_web_socket.close()
        pass

    def run(self):
        """ Wait for incoming requests"""
        self.m_web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.m_web_socket.bind((self.m_web_addr[0], self.m_web_addr[1]))
        self.m_web_socket.listen(15)

        x_read_list  = [self.m_web_socket]
        # aWebSocket.settimeout(60)
        print(f'websocket {self.m_web_addr[0]} at {self.m_web_addr[1]}')

        while self.m_running:
            x_rd, x_wr, x_err = select.select(x_read_list, [], x_read_list)
            if not x_rd and not x_wr and not x_err:
                continue
                            
            for x_socket in x_err:
                if x_socket is self.m_web_socket:
                    x_socket.close()
                    x_read_list.remove(x_socket)
                    print('server socket closed')
                    raise
                else:
                    x_read_list.remove(x_socket)
                    x_socket.close()
                    self.m_clients.pop(x_socket)

            for x_socket in x_rd:
                if x_socket is self.m_web_socket:
                    x_clt_addr = self.m_web_socket.accept()
                    self.m_clients[x_clt_addr[0]] = TWebSocketClient(x_clt_addr, self.m_web_addr, self.m_agent_class)
                    x_read_list.append(x_clt_addr[0])
                else:
                    x_client: TWebSocketClient = self.m_clients.get(x_socket)
                    try:
                        x_client.handle_request()
                    except (TWebSocketException, ConnectionResetError, ConnectionAbortedError) as aEx:
                        x_client.shutdown()
                        x_socket.close()
                        x_read_list.remove(x_socket)
                        self.m_clients.pop(x_socket)


class TWebAsyncManager(threading.Thread):
    def __init__(self, target: Callable, condition: threading.Condition):
        self.m_target  = target
        self.m_cv      = condition
        self.m_running = True

        super().__init__()

    def shutdown(self):
        with self.m_cv:
            self.m_running = False
            self.m_cv.notify_all()

    def run(self):
        while self.m_running:
            self.m_target()
            with self.m_cv:
                self.m_cv.wait()




