# -*- coding: utf-8 -*-
"""
    Copyright (C) 2015 www.EEZZ.biz (haftungsbeschränkt)

    TBluetooth:
    singleton to drive the bluetooth interface
    

"""
import os
import ctypes
import select
from   threading       import Thread, Lock
from   table           import TTable
from   service         import singleton

import bluetooth
from   bluetooth       import BluetoothSocket
import base64

from   Crypto          import Random
from   itertools       import zip_longest
import json 
import winreg
import struct
import time
from   Crypto.PublicKey import RSA
from   Crypto.Cipher    import PKCS1_v1_5
from   Crypto.Hash      import MD5
from   enum             import Enum
import gettext

_ = gettext.gettext


class ErrorCodes(Enum):
    TIMEOUT:            1100
    PW_CHECK:           1101
    PW_EVALUATION:      1102
    DEVICE_SELECTION:   1104
    DEVICE_RANGE:       1105
    ATTRIBUTES:         1106


@singleton
class TBluetooth(TTable):
    """  """
    def __init__(self):
        # noinspection PyArgumentList
        super().__init__(column_names=['Address', 'Name'], title='bluetooth devices')
        self.m_lock        = Lock()
        self.m_service     = TBluetoothService()
        self.lock_workstation = None

        # start lock terminal thread
        # wait for user to call find_devices in a thread

    def find_devices(self) -> None:
        """ Should be called frequently to show new devices in range. All access to the list
         has to be thread save in this case """
        x_result = bluetooth.discover_devices(flush_cache=True, lookup_names=True)
        with self.m_lock:
            self.data.clear()
            for x_item in x_result:
                x_address, x_name = x_item
                self.append([x_address, x_name])
            self.do_sort(1)

    def unlock_workstation(self) -> dict:
        x_result = self.get_user_passwd()
        if not (self.lock_workstation and self.lock_workstation.is_alive()):
            if x_result['return']['code'] == 200:
                self.lock_workstation = TLockWorkstation(x_result['address'])
                self.lock_workstation.start()
        return x_result

    def get_user_passwd(self) -> dict | None:
        """ """
        for x_row in self.get_visible_rows():
            x_address, x_name = [x.value for x in x_row.cells]

            x_user_entry = str()
            # self.mDatabase.getUser(x_address)
            if not x_user_entry:
                continue

            x_cid, x_name, x_sid, x_vector64, x_rsa_key = x_user_entry
            x_rsa_key = RSA.importKey(x_rsa_key)
            x_vector  = base64.b64decode(x_vector64)

            # Send password request to the device:
            x_response = self.m_service.send_request(x_address, {"command": "GETUSR", "args": [x_sid]})
            if x_response['return']['code'] != 200:
                continue

            try:
                x_jsn_pwd_enc64 = x_response['return']['encrypted']
                x_jsn_pwd_encr  = base64.b64decode(x_jsn_pwd_enc64)
                x_encryptor     = PKCS1_v1_5.new(x_rsa_key)
                x_jsn_pwd_str   = x_encryptor.decrypt(x_jsn_pwd_encr, x_vector).decode('utf8')
                # xJsnPwdStr    = xRsaKey.decrypt(xJsnPwdEncr).decode('utf-8')

                x_jsn_pwd       = json.loads(x_jsn_pwd_str)
                x_pwd_encr64    = x_jsn_pwd['password'].encode('utf-8')
                x_pwd_encr      = base64.b64decode(x_pwd_encr64)
                x_timestamp     = x_jsn_pwd['time']

                # Define a timeout for secure communication
                if abs(time.time() - x_timestamp / 1000) > 100:
                    return {"return": {"code": ErrorCodes.TIMEOUT.value, "value": "timeout"}}

                x_pwd_clear = b''.join([bytes([(x ^ y) & 0xff]) for x, y in zip(x_pwd_encr, x_vector)])
                x_pwd_clear = x_pwd_clear[:].decode('utf-8')
            except Exception as x_ex:
                return {"return": {"code": 1120, "value": x_ex}}

            x_response = {"address": x_address, "return": {"code": 200, "value": "GETUSR", "args": [x_sid, x_pwd_clear]}}
            return x_response

    def set_user_password(self, device_address: str, device_name: str, user: str, sid: str, password: str) -> dict:
        """ Stores the user password on mobile device
        """
        x_response = {"return": {"code": 510, "value": "No bluetooth device in Range"}}

        x_vector   = Random.new().read(16)
        x_vector64 = base64.b64encode(x_vector)
        x_pwd_len  = len(password)

        if x_pwd_len < 6:
            return {"return": {"code": ErrorCodes.PW_CHECK.value, "value": "password check failed"}}
        if len(device_address) < 5 or len(device_name) < 1:
            return {"return": {"code": ErrorCodes.PW_CHECK.value, "value": "no device selected"}}

        x_pwd_encr   = b''.join([bytes([(int(x) ^ y) & 0xff]) for x, y in zip_longest(password.encode('utf8'), x_vector, fillvalue=0)])
        x_pwd_encr64 = base64.b64encode(x_pwd_encr).decode('utf8')

        try:
            # Store the base vector in registry
            x_device_hdl = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, 'Software\\eezz\\assoc', 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(x_device_hdl, sid, None, winreg.REG_BINARY, int.from_bytes(x_vector))
        except Exception as xEx:
            pass

        try:
            # Store the challenge in registry
            x_rsa_pub_key = ""
            # self.mDatabase.registerUser(device_address, device_name, user, sid, x_vector64)
            x_arr_pub_key = [xLine for xLine in x_rsa_pub_key.split('\n') if not ('----' in xLine)]
            x_rsa_pub_key = ''.join(x_arr_pub_key)

            x_response = self.m_service.send_request(device_address, {"command": "SETUSR", "args": [sid, x_pwd_encr64, x_rsa_pub_key]})
            if x_response['return']['code'] != 200:
                return x_response

        except Exception as xEx:
            x_response = {"return": {"code": 517, "value": "register to database failed", "args": [str(xEx)]}}

        if x_response['return']['code'] == 200:
            # xMessage = {"return": {"code": 200, "value": "GETUSR", "args": [sid, password]}}
            x_response['return']['args'] = [_("Password successfully stored on device")]
        return x_response

    def register_user(self, address: str, alias: str = '', fname: str = '', lname: str = '', email: str = '', iban: str = '', password: str = '') -> dict:
        """ Register user on the mobile device
        :param address:  Address of the mobile device
        :param alias:    Display bane of the user
        :param fname:    First name
        :param lname:    Last name
        :param email:    E-Mail address
        :param iban:     Payment account
        :param password: Password
        :return:         Status message
        """
        if not address:
            x_response = {"return": {"code": ErrorCodes.DEVICE_RANGE.value, "value": "no device in range"}}
            return x_response

        if not email or not iban or not password or not alias:
            x_response = {"return": {"code": ErrorCodes.ATTRIBUTES.value, "value": "mandatory fields missing"}}
            return x_response

        x_hash_md5 = MD5.new(password.encode('utf8'))
        x_address  = address  # self.mDevices.get_selected_row()[1]
        x_request  = {"command": "Register",
                      "args":  [x_hash_md5.hexdigest(), ''],
                      "TUser": {"CEmail": email, "CNameAlias": alias, "CNameFirst": fname, "CNameLast": lname, "CIban": iban}}
        x_response = self.m_service.send_request(x_address, x_request)
        x_response['address'] = x_address

        if x_response['return']['code'] == 200:
            # self.mDatabase.setSim(x_address, x_response['TDevice']['CSim'])
            x_response['return']['args'] = [_('Reply to verification E-Mail to accomplish registration')]
        return x_response

    def get_eezz_key(self, address):
        """ """
        if not address:
            return {'return': {'code': ErrorCodes.ATTRIBUTES.value, 'value': 'Device Address missing'}}

        # Get key from selected device
        x_request = {"command": "GETKEY", "args": []}
        x_response = self.m_service.send_request(address, x_request)
        x_response['address'] = address
        return x_response

    def get_visible_rows(self, get_all=False) -> list:
        """ thread save access to the table entries
        :return: all table rows
        """
        with self.m_lock:
            return super().get_visible_rows(get_all=True)


@singleton
class TUserAccount(TTable):
    """  """
    def __init__(self, path: str):
        # noinspection PyArgumentList
        super().__init__(column_names=['Caption', 'SID'], title='Users')
        self.m_hostname = str()
        self.read_windows_registry()

    def read_windows_registry(self):
        try:
            x_profile_list_hdl = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ProfileList')

            for i in range(15):
                x_sid         = winreg.EnumKey(x_profile_list_hdl, i)
                x_profile_key = winreg.OpenKey(x_profile_list_hdl, x_sid)

                # pick only local users
                x_image_path  = winreg.QueryValueEx(x_profile_key, 'ProfileImagePath')
                x_sid_binary  = winreg.QueryValueEx(x_profile_key, 'Sid')
                x_sid_person  = struct.unpack('qi', x_sid_binary[0][:12])
                if x_sid_person[1] != 21:
                    continue

                x_parts       = x_image_path[0].split(os.sep)
                x_user        = x_parts[-1]

                self.append([x_user, x_sid])

                x_tcp_ip_hdl    = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters')
                x_hostname      = winreg.QueryValueEx(x_tcp_ip_hdl, 'hostname')
                self.m_hostname = x_hostname[0]
        except OSError:
            return


class TLockWorkstation(Thread):
    def __init__(self, address: str):
        super().__init__(daemon=True, name='LockWorkstation')
        self.m_address = address
        self.m_service = TBluetoothService()

    def run(self):
        while True:
            x_response = self.m_service.send_request(self.m_address, {'command': 'PING'})
            if x_response['return']['code'] != 200 and x_response['return']['code'] != 100:
                ctypes.windll.user32.LockWorkStation()
                break
            time.sleep(2)


@singleton
class TBluetoothService:
    def __init__(self, bt_service, bt_address):
        self.bt_service  = bt_service
        self.bt_address  = bt_address
        self.m_lock      = Lock()
        self.bt_socket   = None

    def send_request(self, address: str, message: dict) -> dict:
        with self.m_lock:
            # Connect to the selected bluetooth device
            x_service = bluetooth.find_service(uuid=self.bt_service, address=address)
            x_socket  = BluetoothSocket(bluetooth.RFCOMM)
            x_timeout = 100

            for x in x_service:
                x_socket.connect((x['host'], x['port']))
                break

            # Send request: Wait for writer and send message
            x_rd, x_wr, x_err = select.select([], [x_socket], [x_socket], 0.2)
            if x_err or not x_wr:
                return dict()
            for x_writer in x_wr:
                x_writer.send(json.dumps(message).encode('utf8'))
                break

            # receive an answer
            while True:
                try:
                    x_rd, x_wr, x_err = select.select([x_socket], [], [x_socket], x_timeout)
                    if x_err:
                        x_result   = x_socket.recv(1024)
                        x_response = {"return": {"code": 514, "value": x_result.decode('utf-8')}}
                        break
                    elif x_rd:
                        x_result   = x_socket.recv(1024)
                        x_result   = x_result.decode('utf8').split('\n')[-2]
                        x_response = json.loads(x_result)
                        break
                    else:
                        raise OSError('timeout')

                except OSError as xEx:
                    return dict()
            return x_response


if __name__ == '__main__':
    """ Main entry point for mdule tests
    """
    exit()

   