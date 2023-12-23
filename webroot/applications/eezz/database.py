# -*- coding: utf-8 -*-
"""
    Copyright (C) 2015 www.EEZZ.biz (haftungsbeschränkt)

    TDatabase
    Create database from scratch.
    Encapsulate database access.
    Manage the RSA public key for communication with eezz server
    
"""
import os
import base64
from   Crypto.PublicKey import RSA
import sqlite3
import json
from   service import TService


class TDatabase:
    """ EEZZ database """
    def __init__(self):
        x_mod  = int("C5F23FA172317A1F6930C0F9AF79FF044D34BFD1336E5A174155953487A4FF0C744A093CA7044F39842AC685AB37C55F1F01F0055561BAD9C3EEA22B28D09F061875ED5BDB2F1F2B797B1BEF6534C0D4FCEFAFFA8F3A91396961165241564BD6E3CA08023F2A760A0B54A4A6A996CDF7DE3491468C199566EE5993FCFD03A2B285AD6FBBC014A20C801618EE19F88EB8E6359624A35FDD7976F316D6AB225CF85DA5E63AB30248D38297A835CF16B9799973C2F9F05F5F850B3152B3A05F06FEC0FBDA95C70911F59F6A11A1451822ABFE4FE5A021F7EA983BDE9F442302891DCF51B7322EAFB88950F2617B7120F9B87534719DCA27E87D82A183CB37BC7045", 16)
        x_exp  = int("10001", 16)
        x_key  = RSA.construct((x_mod, x_exp))

        x_service       = TService()
        self.public_Key = x_key
        self.location   = os.path.join(x_service.document_path, 'eezz.db')
        
        if not os.path.exists(self.location):
            os.makedirs(os.path.join(x_service.document_path), exist_ok=True)
            x_database = sqlite3.connect(self.location)
            x_cursor   = x_database.cursor()
            x_cursor.execute('create table TDocuments (CID text not null, CAddr text not null, CKey  text, CDescr text, CLink text, CStatus text, CTitle text, CAuthor text, PRIMARY KEY (CID, CAddr) )')
            x_cursor.execute('create table TDevices   (CID text PRIMARY KEY, CName text, CKey  text, CIMEI text)')
            x_cursor.execute('create table TUser      (CID text PRIMARY KEY, CName text, CSid  text, CPasswd  text)')
            x_database.commit()
            x_database.close()

        self.mUserTable = TDbTable(self.mLocation, 
                                   {'select':['TDevices.CID as Address', 'TDevices.CName as Device', 'TUser.CName as User', 'TUser.CSid as CSid', 'TUser.CPasswd as Passwd'], 
                                    'from'  :['TUser, TDevices'], 
                                    'where' : 'TUser.CID=TDevices.CID'})
        
        self.mDocuments = TDbTable(self.mLocation,
                                   {'select':['CID','CTitle','CStatus','CDescr', 'CAddr'],
                                    'from'  :['TDocuments'],
                                    'where' : 'CAddr=?'})
        
    def getUserTable(self):
        """ self.mUserTable.do_navigate() """
        return self.mUserTable.get_selected_obj()
    
    def getDocTable(self, address, visible_items, visible_block):
        return self.mDocuments.get_selected_obj(-1, visible_items, visible_block, (address,))
        
    def getEezzPublic(self):
        return self.mPublicKey

    def registerDevice(self, aAddress, aName, aKey):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('insert or replace into TDevices (CID, CName, CKey) values (?,?,?)', (aAddress, aName, aKey))
            x_database.commit()
        except sqlite3.Error as xEx:
            pass
        finally:
            x_cursor.close()
            x_database.close()

    def setSim(self, aAddress, aSim):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('update TDevices set CIMEI=? where CID=?', (aSim, aAddress))
            x_database.commit()
        except sqlite3.Error as xEx:
            pass
        finally:
            x_cursor.close()
            x_database.close()

    def getSim(self, aAddress):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('select CIMEI from TDevices where CID=?', (aAddress,))
            xSim      = x_cursor.fetchone()[0]
        except sqlite3.Error as xEx:
            pass
        finally:
            x_cursor.close()
            x_database.close()
        return xSim
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getDevices(self, aAddress):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            
            if aAddress:
                x_cursor.execute('select CID, CName, CKey from TDevices where CID=?', (aAddress, ))
            else:
                x_cursor.execute('select CID, CName, CKey from TDevices')
                
            xResult   = x_cursor.fetchall()
        except sqlite3.Error as xEx:
            pass
        finally:
            x_cursor.close()
            x_database.close()
        return xResult
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getEezzKey(self, aAddress):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('select CKey from TDevices where CID=?', (aAddress,))
            xKey      = x_cursor.fetchone()[0]
        except sqlite3.Error as xEx:
            pass
        finally:
            x_cursor.close()
            x_database.close()
        return xKey
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def registerUser(self, aAddress, aName, aCaption, aSid, aPasswd):
        xPubKey = None
        
        try:
            x_database  = sqlite3.connect(self.mLocation)
            x_cursor    = x_database.cursor()
            xSelectRes = x_cursor.execute('select CKey from TDevices where CID = ?', (aAddress,))
            
            if xSelectRes.rowcount == -1:
                xRsaKey    = RSA.generate(1024)
                xPrivKey   = xRsaKey.exportKey()
                xSelectRes = x_cursor.execute('insert or replace into TDevices (CID, CName, CKey) values(?,?,?)', (aAddress, aName, xPrivKey))
            else:
                xRsaKey    = x_cursor.fetchone()[0]
                xRsaKey    = RSA.importKey(xRsaKey)
                
            xPubKey = xRsaKey.publickey().exportKey().decode('utf8')    
            x_cursor.execute('insert or replace into TUser (CID, CName, CSid, CPasswd) values (?,?,?,?)', (aAddress, aCaption, aSid, aPasswd))
            x_database.commit()
        except sqlite3.Error as xEx:
            pass
        except Exception as xEx:
            pass
        finally:
            x_database.close()
            self.mUserTable.mExecute = True
        return xPubKey

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getUser(self, aAddress):
        xResult = None
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            xResult   = x_cursor.execute('select CKey from TDevices where CID=?', (aAddress,))            
            xPrivKey  = xResult.fetchone()
            
            if not xPrivKey or not xPrivKey[0]:
                return None
            
            xResult   = x_cursor.execute('select CID, CName, CSid, CPasswd from TUser where CID=?', (aAddress,))
            xUserData = x_cursor.fetchone()
            if not xUserData:
                return None
            
            xResult = xUserData + xPrivKey
        except sqlite3.Error as xEx:
            pass
        except TypeError:
            pass
        finally:
            x_database.close()    
        return xResult
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def removeUser(self, aAddress):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('delete from TUser where CID=?', (aAddress, ))
            x_database.commit()
        except (sqlite3.Error) as xEx:
            pass
        finally:
            x_database.close()
            self.mUserTable.mExecute = True
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getDocument(self, aGuid, aAddress):
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('select CKey, CTitle, CDescr, CStatus from TDocuments where CID=? and CAddr=?', (aGuid, aAddress))
            return x_cursor.fetchone()
        except (sqlite3.Error, TypeError) as xEx:
            pass
        finally:
            x_database.close()
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getKey(self, aGuid):
        xKey = str()
        
        try:
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('select CKey from TDocuments where CID=?', (aGuid,))
            xKey      = x_cursor.fetchone()[0]
        except (sqlite3.Error, TypeError) as xEx:
            pass
        finally:
            x_database.close()
            
        return xKey
    
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def insertKey(self, aGuid, aKey, aAddress, aTitle, aDescr, aLink, aStatus):
        """ Insert a document key """
        x_cursor = None
        if isinstance(aDescr, dict):
            aDescr = json.dumps(aDescr)
        
        try:    
            x_database = sqlite3.connect(self.mLocation)
            x_cursor   = x_database.cursor()
            x_cursor.execute('insert or replace into TDocuments (CID, CKey, CAddr, CTitle, CDescr, CLink, CStatus) values (?,?,?,?,?,?,?)', 
                            (aGuid, aKey, aAddress, aTitle, aDescr, aLink, aStatus))
            x_database.commit()
        except sqlite3.Error as xEx:
            pass
        finally:
            if x_cursor:
                x_cursor.close()
            if x_database:
                x_database.close()

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    def getLocation(self):
        return self.mLocation


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == '__main__':
    pass
