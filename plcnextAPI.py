# Libraries to import
import requests
import urllib3
import json
import datetime
import logging
import time

deviceInputData = {
    "isAvailable": False,
    "state": "",
    "timestamp": "",
    "metrics": []
}


def readString(varNameList):
    # Defining tags
    readStr = ''
    # Creating the readString
    for varName in varNameList:
        readStr = readStr + varName + ','
    readStr = readStr[:-1]
    return readStr


class REST:
    # Creating HTTP session for the API connection, with access token if required
    def __init__(self, auth, username, password):
        self.session = requests.Session()
        self.auth = auth
        if auth:
            payload = {"scope": "variables"}
            accessToken = self.session.request('POST', 'https://localhost/_pxc_api/v1.2/auth/auth-token', data=json.dumps(payload), verify=False)
            payload2 = {"code": json.loads(accessToken.content)['code'], "grant_type": "authorization_code", "username": username, "password": password}
            time.sleep(1.0)
            authToken = self.session.request('POST', 'https://localhost/_pxc_api/v1.2/auth/access-token', data=json.dumps(payload2), verify=False)
            self.headers = {"Authorization": json.loads(authToken.content)['access_token']}
            self.key = json.loads(authToken.content)['access_token']

    # Building the dictionary
    def buildDictionary(self):
        # Defining vars
        varNameList = []
        varTypeList = []
        # Defining globals
        global deviceInputData
        # Adding to log current state
        logging.info('API State: Data dictionary updated started')
        deviceInputData['state'] = 'API State: Data dictionary updated started'
        # Requesting the dictionary
        if self.auth:
            payload = self.session.request('GET', 'https://localhost/ehmi/data.dictionary.json', headers=self.headers, verify=False)
        else:
            payload = self.session.request('GET', 'https://localhost/ehmi/data.dictionary.json', verify=False)
        # Checking to make sure response is OK
        if payload.status_code == 200:
            deviceInputData['isAvailable'] = True
            deviceInputData['state'] = 'API State: Updating data dictionary...'
            # Data pre-processing
            dictionary = json.loads(payload.content)
            for key in dictionary['HmiVariables2']:
                varNameList.append(key[13:])
                varTypeList.append(dictionary['HmiVariables2'][key]['Type'])
        elif payload.status_code == 404:
            logging.info('API State: Unavailable')
            deviceInputData['isAvailable'] = False
            deviceInputData['state'] = 'API State: Unavailable (did you download a PLCnext project with an HMI component yet?)'
        else:
            logging.info('API State: Unavailable')
            deviceInputData['isAvailable'] = False
            deviceInputData['state'] = 'API State: Unknown Error'

        return varNameList, varTypeList

    # Reading tags from the API
    def readAPI(self, varNameList, varTypeList):
        # Defining vars
        index = 0
        varObj = {}
        varList = []
        # Defining globals
        global deviceInputData
        # Building URL and headers
        URL = 'https://localhost/_pxc_api/api/variables/?pathPrefix=Arp.Plc.Eclr/&paths=' + readString(varNameList)
        # API Request
        if self.auth:
            payload = self.session.request('GET', URL, headers=self.headers, verify=False)
        else:
            payload = self.session.request('GET', URL, verify=False)
        # Checking to make sure response is OK
        if payload.status_code == 200:
            logging.info("API State: New API data received")
            deviceInputData['isAvailable'] = True
            deviceInputData['state'] = 'API State: New API data received'
            deviceInputData['timestamp'] = str(datetime.datetime.now())
            # Data pre-processing
            variables = json.loads(payload.content)
            for var in variables['variables']:
                varObj.clear()
                varObj['name'] = var['path'][13:]
                varObj['value'] = var['value']
                varObj['type'] = varTypeList[index]
                varList.append(varObj.copy())
                index = index+1
            deviceInputData['metrics'] = varList
        elif payload.status_code == 404:
            logging.info('API State: Unavailable')
            deviceInputData['isAvailable'] = False
            deviceInputData['state'] = 'API State: Unavailable (did you download a PLCnext project with an HMI component yet?)'
        else:
            logging.info('API State: Unavailable')
            deviceInputData['isAvailable'] = False
            deviceInputData['state'] = 'API State: Unknown Error'
        return deviceInputData

    def writeAPI(self, variables):
        # Defining vars
        varObj = {}
        varList = []
        URL = 'https://localhost/_pxc_api/api/variables/'
        # Check if auth is used
        if self.auth:
            header = {"Content-Type": "application/json;charset=UTF-8", "Authorization": self.key}
        else:
            header = {"Content-Type": "application/json;charset=UTF-8"}
        # Data pre-processing
        for var in variables:
            varObj.clear()
            varObj['path'] = var['name']
            varObj['value'] = var['value']
            varObj['valueType'] = "Constant"
            varList.append(varObj.copy())
        payload = {"pathPrefix": "Arp.Plc.Eclr/", "variables": varList}
        self.session.put(URL, headers=header, data=json.dumps(payload), verify=False)


def getData(waitTime, auth, username, password):
    time.sleep(waitTime)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    api = REST(auth, username, password)
    tagNames, tagTypes = api.buildDictionary()
    variables = api.readAPI(tagNames, tagTypes)
    return variables


def postData(waitTime, variables, auth, username, password):
    time.sleep(waitTime)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    api = REST(auth, username, password)
    api.writeAPI(variables)
