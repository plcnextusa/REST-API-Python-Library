# Libraries to import
import requests
import urllib3
import json
from datetime import datetime
import time
import logging
from logging.handlers import RotatingFileHandler
import threading


# Trigger for pulling data from PLCnext Engineer
def trigger2hr(trigger):
    return ((int(datetime.now().strftime('%H')) % 2 == 0 or int(datetime.now().strftime('%H')) == 0) and int(datetime.now().strftime('%M')) == 0) and not trigger


# Reset 15 minute trigger
def reset2hrTrigger():
    return not ((int(datetime.now().strftime('%H')) % 2 == 0 or int(datetime.now().strftime('%H')) == 0) and int(datetime.now().strftime('%M')) == 0)


def readString(varNameList):
    # Defining tags
    readStr = ''
    # Creating the readString
    for varName in varNameList:
        readStr = readStr + varName + ','
    readStr = readStr[:-1]
    return readStr


class REST:
    # Get token for verification
    def __init__(self, credentials=None, logfileNameLocation='/opt/plcnext/logs/API.log', logfileSize=1000000, logfileBackupCount=1):
        # Disable warnings for Insecure HTTP requests to PLC REST API (SSL)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # Initialize log file
        logging.basicConfig(
            handlers=[RotatingFileHandler(logfileNameLocation, maxBytes=logfileSize, backupCount=logfileBackupCount)],
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        self.session = requests.Session()
        self.credentials = credentials
        self.sessionID = ''
        self.headers = ''
        self.authLatch = False
        self.sessionLatch = False
        self.dictBuilt = False
        self.variableDict = []

    def createSession(self):
        sessionExists = bool()
        try:
            sessionExistResponse = self.session.request('GET', 'https://localhost/_pxc_api/api/sessions', verify=False)
            if 'sessions' in json.loads(sessionExistResponse.content):
                self.sessionLatch = False
                sessions = json.loads(sessionExistResponse.content)['sessions']
                for session in sessions:
                    if session['stationID'] == '1' and not self.authLatch:
                        self.sessionID = session['id']
                        logging.info(f'Session Exists with ID {self.sessionID}')
                        sessionExists = True
                if not sessionExists:
                    payload = 'stationID=1&timeout=10800000'
                    creationResponse = self.session.request('POST', 'https://localhost/_pxc_api/api/sessions', data=payload, verify=False)
                    if creationResponse.status_code == 201:
                        self.sessionID = json.loads(creationResponse.content)['sessionID']
                        return True
                    elif creationResponse.status_code == 409:
                        self.sessionID = json.loads(creationResponse.content)['error']['details'][0]['values'][0]
                        return True
                    else:
                        logging.info(f'Error in Session Creation. Returned Status Code: {creationResponse.status_code} Response: {json.loads(creationResponse.content)["error"]["details"][0]["reason"]}')
                        return False
                else:
                    return True
            else:
                if not self.sessionLatch:
                    logging.info(f'PLC returned error: {json.loads(sessionExistResponse.content)}')
                    self.sessionLatch = True
        except Exception as e:
            logging.info(f'Exception on session creation: {repr(e)}')
            return False

    # Refresh API session
    def refreshSession(self):
        try:
            Found = False
            response = self.session.request('POST', f'https://localhost/_pxc_api/api/sessions/{self.sessionID}', verify=False)
            if response.status_code == 200:
                return True
            elif json.loads(response.content)["error"]["details"][0]["reason"] == 'invalidSessionID':
                sessionExistResponse = self.session.request('GET', 'https://localhost/_pxc_api/api/sessions', verify=False)
                sessions = json.loads(sessionExistResponse.content)['sessions']
                for session in sessions:
                    if session['stationID'] == '1':
                        Found = True
                        self.sessionID = session['id']
                if len(sessions) > 0 and Found:
                    response = self.session.request('POST', f'https://localhost/_pxc_api/api/sessions/{self.sessionID}', verify=False)
                    if response.status_code == 200:
                        return True
                    else:
                        logging.info(f'Server rejected refresh token after getting correct ID with Status Code: {response.status_code} Response: {json.loads(response.content)["error"]["details"][0]["reason"]}')
                        return False
                else:
                    creationStatus = self.createSession()
                    if creationStatus:
                        return True
                    else:
                        logging.info(f'Creating session on refresh if does not exist fails.')
                        return False
            else:
                logging.info(f'Server rejected refresh token with Status Code: {response.status_code} Response: {json.loads(response.content)["error"]["details"][0]["reason"]}')
                return False
        except Exception as e:
            logging.info(f'Exception on session refresh: {repr(e)}')
            return False

    # API authentication token handle
    def authSignIn(self):
        try:
            if self.credentials:
                payload = {"scope": "variables"}
                accessToken = self.session.request('POST', 'https://localhost/_pxc_api/v1.2/auth/auth-token', data=json.dumps(payload), verify=False)
                payload2 = {"code": json.loads(accessToken.content)['code'], "grant_type": "authorization_code", "username": self.credentials[0], "password": self.credentials[1]}
                authToken = self.session.request('POST', 'https://localhost/_pxc_api/v1.2/auth/access-token', data=json.dumps(payload2), verify=False)
                if authToken.status_code == 200:
                    if self.authLatch:
                        logging.info(f'Auth token created successfully after failure.')
                    self.authLatch = False
                    self.headers = {"Authorization": json.loads(authToken.content)['access_token']}
                    if self.headers['Authorization'] != '':
                        return True
                elif authToken.status_code == 401 and json.loads(authToken.content)["error"]["details"][0]["reason"] == "wrongPassword" and not self.authLatch:
                    self.authLatch = True
                    logging.info(f'User does not exist or password is incorrect!')
                    return False
                elif authToken.status_code == 401 and not self.authLatch:
                    self.authLatch = True
                    logging.info(f'Unknown error occured with token handle: {json.loads(authToken.content)["error"]["details"][0]["reason"]}')
                    return False
                elif authToken.status_code >= 300 and not self.authLatch:
                    self.authLatch = True
                    logging.info(f'Unknown error code {authToken.status_code} on token handle with error: {json.loads(authToken.content)["error"]["details"][0]["reason"]}')
                    return False
                else:
                    return False
            else:
                return True
        except Exception as e:
            logging.info(f'Exception on API authentication token handle: {e}')

    def buildDict(self):
        dictionary = None
        try:
            if not self.authLatch and not self.dictBuilt:
                self.variableDict.clear()
                URL = 'https://localhost/ehmi/data.dictionary.json'
                dictionary = json.loads(self.session.request('GET', URL, headers=self.headers, verify=False).content)
                # If Authorization fails, re-authenticate then request again if login is successful.
                if 'error' in dictionary:
                    if dictionary['error']["details"][0]["reason"] == 'accessDenied':
                        logging.info(f'Buid Dict error: {dictionary["error"]["details"][0]["reason"]}. Refreshing Token.')
                        success = self.authSignIn()
                        if success:
                            URL = 'https://localhost/ehmi/data.dictionary.json'
                            dictionary = json.loads(self.session.request('GET', URL, headers=self.headers, verify=False).content)
                            for key in dictionary['HmiVariables2']:
                                self.variableDict.append(key[13:])
                                self.dictBuilt = True
                            return self.variableDict
                        else:
                            logging.info(f'Buid Dict log in failed.')
                            return None
                    # If request rejected for another reason catch here
                    else:
                        logging.info(f'Buid Dict returned unknown HTTP error: {dictionary["error"]["details"][0]["reason"]}')
                else:
                    for key in dictionary['HmiVariables2']:
                        self.variableDict.append(key[13:])
                        self.dictBuilt = True
                    return self.variableDict
            elif self.dictBuilt:
                return self.variableDict
        except Exception as e:
            logging.info(f'Exception on Buid Dict: {repr(e)}')
            logging.info(f'Payload: {dictionary}')
            return None

    def readAPI(self, varNames: list):
        variables = None
        varObj = {}
        varList = []
        try:
            if not self.authLatch:
                URL = 'https://localhost/_pxc_api/api/variables?pathPrefix=Arp.Plc.Eclr/&paths=' + readString(varNames)
                variables = json.loads(self.session.request('GET', URL, headers=self.headers, verify=False).content)
                # If Authorization fails, re-authenticate then request again if login is successful.
                if 'error' in variables:
                    if variables['error']["details"][0]["reason"] == 'accessDenied':
                        logging.info(f'Read API error: {variables["error"]["details"][0]["reason"]}. Refreshing Token.')
                        success = self.authSignIn()
                        if success:
                            URL = 'https://localhost/_pxc_api/api/variables?pathPrefix=Arp.Plc.Eclr/&paths='+ readString(varNames)
                            variables = json.loads(self.session.request('GET', URL, headers=self.headers, verify=False).content)
                            for var in variables['variables']:
                                varObj.clear()
                                varObj['name'] = var['path'][13:]
                                varObj['value'] = var['value']
                                varList.append(varObj.copy())
                            return varList
                        else:
                            logging.info(f'Read API log in failed.')
                            return None
                    # If request rejected for another reason catch here
                    else:
                        logging.info(f'Read API returned unknown HTTP error: {variables["error"]["details"][0]["reason"]}')
                else:
                    for var in variables['variables']:
                        varObj.clear()
                        varObj['name'] = var['path'][13:]
                        varObj['value'] = var['value']
                        varList.append(varObj.copy())
                    return varList
        except Exception as e:
            logging.info(f'Exception on Read API: {repr(e)}')
            logging.info(f'Payload: {variables}')
            return None

    def writeAPI(self, varStruct: dict):
        varObj = {}
        variables = []
        try:
            for var in varStruct:
                varObj.clear()
                varObj['path'] = var['name']
                varObj['value'] = var['value']
                varObj['valueType'] = "Constant"
                variables.append(varObj.copy())
            URL = 'https://localhost/_pxc_api/api/variables/'
            payload = {"pathPrefix": "Arp.Plc.Eclr/", "variables": variables}
            status = self.session.request("PUT", URL, headers=self.headers, data=json.dumps(payload), verify=False)
            if status.status_code == 200:
                return True
            else:
                logging.error(f'Write variable returned code: {status.status_code} Reason: {status}')
                return False
        except Exception as e:
            logging.info(f'Exception on Write API: {repr(e)}')
            return False


class API:
    def __init__(self, credentials=None, logfileNameLocation='/opt/plcnext/logs/API.log', logfileSize=1000000, logfileBackupCount=1):
        self.trigger2hr = False
        self.refreshed = False
        # Init PLCnext data class
        self.data = REST(credentials, logfileNameLocation, logfileSize, logfileBackupCount)
        # Start PLCnext data session
        self.sessionCreated = self.data.createSession()
        # Authenticate PLCnext data session if session created. If not created it will try and create in loop.
        if self.sessionCreated:
            self.loggedIn = self.data.authSignIn()

    def read(self, variables: list):
        # Check to see if session created and logged in
        if not (self.sessionCreated and self.loggedIn):
            # Start PLCnext data session
            self.sessionCreated = self.data.createSession()
            # Authenticate PLCnext data session
            self.loggedIn = self.data.authSignIn()

        # 2 hour RTC trigger to maintain session
        if trigger2hr(self.trigger2hr):
            self.refreshed = self.data.refreshSession()
            if self.refreshed:
                self.trigger2hr = True

            # 2 hour RTC trigger variable if not at 2 hour interval
            if reset2hrTrigger():
                self.trigger2hr = False
                self.refreshed = False
        return self.data.readAPI(varNames=variables)

    def readAll(self):
        # Check to see if session created and logged in
        if not (self.sessionCreated and self.loggedIn):
            # Start PLCnext data session
            self.sessionCreated = self.data.createSession()
            # Authenticate PLCnext data session
            self.loggedIn = self.data.authSignIn()

        # 2 hour RTC trigger to maintain session
        if trigger2hr(self.trigger2hr):
            self.refreshed = self.data.refreshSession()
            if self.refreshed:
                self.trigger2hr = True

            # 2 hour RTC trigger variable if not at 2 hour interval
            if reset2hrTrigger():
                self.trigger2hr = False
                self.refreshed = False
        return self.data.readAPI(varNames=self.data.buildDict())

    def write(self, variables: dict):
        # Check to see if session created and logged in
        if not (self.sessionCreated and self.loggedIn):
            # Start PLCnext data session
            self.sessionCreated = self.data.createSession()
            # Authenticate PLCnext data session
            self.loggedIn = self.data.authSignIn()

        # 2 hour RTC trigger to maintain session
        if trigger2hr(self.trigger2hr):
            self.refreshed = self.data.refreshSession()
            if self.refreshed:
                self.trigger2hr = True

            # 2 hour RTC trigger variable if not at 2 hour interval
            if reset2hrTrigger():
                self.trigger2hr = False
                self.refreshed = False
        # Check to make sure list of dicts has correct structure
        for var in variables:
            if 'name' and 'value' in var:
                pass
            else:
                logging.error(f"Variable structure not correct. Expecting [['name': NAME,'value': VALUE],['name': NAME,'value': VALUE]...] got {variables}")
                return False

        return self.data.writeAPI(varStruct=variables)