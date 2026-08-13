# Python included libraries to import
import sys
import json
import logging
from dataclasses import dataclass
from typing import Any
from datetime import datetime, timedelta, timezone
# Pip installed libraries to import
try:
    import requests
    import urllib3
except ImportError:
    logging.error("Required library not found. Please install the 'requests' library using the command 'pip install requests'.")
    sys.exit(1)
    raise


class PLCnextAPI:
######################
# EXPOSED FUNCTIONS
######################
    # ===============================================================
    # Class Initialization
    # ===============================================================
    def __init__(self, ip='localhost', requestTimeout=5, sessionTimeout=10800000, stationID="1"):
        """
        Initializes the PLCnextAPI class with the provided IP address (if not on localhost), timeout, and station ID.
        """
        # Static paths
        self.SESSIONS_URL = f'https://{ip}/_pxc_api/v1.2/sessions'
        self.AUTH_URL = f'https://{ip}/_pxc_api/v1.2/auth'
        self.VARIABLES_URL = f'https://{ip}/_pxc_api/api/variables'
        self.DICTIONARY_URL = f'https://{ip}/ehmi/data.dictionary.json'
        self.GROUPS_URL = f'https://{ip}/_pxc_api/api/groups'
        self.PATH_PREFIX = 'Arp.Plc.Eclr/'
        # Disable warnings for Insecure HTTP requests to PLC REST API (SSL)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # Start the logger if the user wants to log the output of the REST API.
        self.logger = logging.getLogger(name=__name__)
        self.logger.addHandler(logging.NullHandler())
        # All other parameters for the REST API are set here.
        self.session = requests.Session()
        self.username = None
        self.password = None
        self.sessionCreatedTime = None
        self.authentication = False
        self.sessionTimeout = sessionTimeout
        self.requestTimeout = requestTimeout
        self.stationID = stationID
        self.sessionID = None
        self.headers = {}
        self.variableDict = []
        self.logger.info(f'PLCnextAPI initialized with stationID: {self.stationID},' 
                         f'session timeout: {self.sessionTimeout}ms and request timeout: {self.requestTimeout}ms')

    # ================================================================
    # Dataclass for the response
    # ================================================================
    @dataclass
    class APIResult:
        success: bool
        data: Any = None
        error: str | None = None

    # ================================================================
    # Connecting to PLCnext API (session creation and authentication)
    # ================================================================
    def connect(self, username=None, password=None) -> APIResult:
        """
        Ensures that a valid PLCnext session exists and the credentials entered are valid.
        """
        try:

            # Update stored credentials if supplied
            if (username is None) ^ (password is None):
                # Raise an error if only one of the username or password is provided
                self.logger.error("Both username and password must be provided together.")
                return self.APIResult(success=False, error ="Both username and password must be provided together.")
    
            elif username is not None and password is not None:
                # Assign the provided username and password to the instance variables and set authentication to True
                self.username = username
                self.password = password
                self.authentication = True
                self.logger.info("Credentials provided. Attempting authentication.")

                if not self._authenticate():
                    self.logger.error("Authentication failed. Please check your username and password.")
                    return self.APIResult(success=False, error ="Authentication failed. Please check your username and password.")

                self.logger.info("Authentication succeeded. Checking for session.")

            # Check if sessionID is None, if so, find or create a session
            if not self.sessionID:

                self.logger.info("No existing session ID found. Searching for the session.")
                # Check if a session already exists for the given stationID
                self._find_session()

                # If no session is found, create a new session
                if not self.sessionID:
        
                    self.logger.info("No existing session ID found. Creating the session.")

                    if not self._create_session():
                        return self.APIResult(success=False, error="Failed to create a session.")
                    
                self.logger.info("Session ID found.")

            if not self._session_needs_refresh():
                self.logger.info("Session ID active.")
                return self.APIResult(success=True)
            
            self.logger.info(f"Session {self.sessionID} approaching timeout. Refreshing.")

            if self._refresh_session():
                self.logger.info("Session ID refreshed.")
                return self.APIResult(success=True)

            # If refreshing the session fails, attempt to create a new session
            self.logger.info("Session ID failed to refresh. Creating a new session")
            self.sessionID = None
            self._create_session()

            # If no session is found, create a new session
            if self.sessionID and self._refresh_session():
                self.logger.info("Session created and no refresh required.")
                return self.APIResult(success=True, error=None) 

            # Catchall for connect method
            self.logger.info("All attempts to create a session failed. Abort.")
            return self.APIResult(success=False, error="Failed to connect to the PLCnext API.")

        except Exception as e:
            self.logger.error(f"Exception occurred while connecting to PLCnext API: {e}")
            return self.APIResult(success=False, error=f"Exception occurred while connecting to PLCnext API: {e}")

    # ================================================================
    # Reading variables
    # ================================================================
    def read(self, variables: list[str]) -> APIResult:
        """
        Read one or more variables from the PLC.

        Example of variables:
            [
                "MotorSpeed",
                "MotorRun"
            ]
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot build variable dictionary.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot read variables.')
            
            # Build the list of variable objects to be sent in the request payload
            response = self.session.get(
                self._create_read_url(variables), 
                headers=self.headers, 
                verify=False, 
                timeout=self.requestTimeout)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to read variables. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, data=None, error=f'Failed to read variables. Status code: {response.status_code}, Reason: {response.content}')
            
            # Return the variables in a parsed dictionary
            results = self._parse_read_response(response.json())
            return self.APIResult(success=True, data=results, error=None)

        except Exception as e:
            self.logger.error(f'Error occurred while reading variables: {repr(e)}')
            return self.APIResult(success=False, data=None, error=f'Error occurred while reading variables: {repr(e)}')

    # ================================================================
    # Writing variables
    # ================================================================
    def write(self, variables: dict) -> APIResult:
        """
        Write one or more variables to the PLC.

        Example of variables:
            {
                "MotorSpeed": 1000,
                "MotorRun": True
            }
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot write variables.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot write variables.')

            # Build the payload for the write command
            payload = {"pathPrefix": self.PATH_PREFIX,
                "variables": [
                    {
                        "path": name,
                        "value": value,
                        "valueType": "Constant"
                    }
                    for name, value in variables.items()
                ]
            }

            # Execute the write command
            response = self.session.put(
                self.VARIABLES_URL, 
                headers=self.headers, 
                data=json.dumps(payload), 
                verify=False, 
                timeout=self.requestTimeout)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to write variable(s). Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, error=f"Failed to write variable(s). Status Code: {response.status_code}")

            return self.APIResult(success=True, error=None)

        except Exception as e:
            self.logger.error(f"Exception occurred while writing variable(s): {repr(e)}")
            return self.APIResult(success=False,error=f"Exception occurred while writing variable(s): {repr(e)}")

    # ================================================================
    # List the current variable groups
    # ================================================================
    def list_groups(self):
        """
        Lists out all existing variable groups.
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot list groups.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot list groups.')
            
            # request the variable group data
            response = self.session.get(
                f"{self.GROUPS_URL}", 
                headers=self.headers, 
                verify=False, 
                timeout=self.requestTimeout)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to list variable groups. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, error=f'Failed to list variable groups. Status code: {response.status_code}, Reason: {response.content}')
            
            # Return the variable groups that exist
            return self.APIResult(success=True, data=response.json()["groups"], error=None)

        except Exception as e:
            self.logger.error(f"Exception occurred while listing groups: {repr(e)}")
            return self.APIResult(success=False,error=f"Exception occurred while listing groups: {repr(e)}")

    # ================================================================
    # Create a variable group
    # ================================================================
    def create_group(self, variables: list[str]) -> APIResult:
        """
        Creates a group of variables that can be requested with one basic command, rather than requesting values individually.

        Array indexes can be specificed using this nomeclature: 
            Array index 2: ArrayName[2]
            Array index 2,4: ArrayName[2; 4]
            Array index 6-8, ArrayName[6-8]
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot create group.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot create group.')

            # Build payload for creating a group and send the request
            payload = {"sessionID": self.sessionID, "pathPrefix": self.PATH_PREFIX, "paths": ",".join(variables)}
            response = self.session.post(
                self.GROUPS_URL, 
                headers=self.headers, 
                data=payload, 
                verify=False, 
                timeout=self.requestTimeout)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to create variable group. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, error=f'Failed to create variable group. Status code: {response.status_code}, Reason: {response.content}')
            
            # Generate the group ID to request the variables
            group_id = response.json()["id"]
            return self.APIResult(success=True, data=group_id, error=None)
              
        except Exception as e:
            self.logger.error(f"Exception occurred while creating a group: {repr(e)}")
            return self.APIResult(success=False,error=f"Exception occurred while creating a group: {repr(e)}")

    # ================================================================
    # Read a variable group
    # ================================================================
    def read_group(self, groupID: str) -> APIResult:
        """
        Reads a defined variable group and outputs them as a dictionary.
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot read group.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot read group.')

            # request the variable group data
            response = self.session.get(
                f"{self.GROUPS_URL}/{groupID}?sessionID={self.sessionID}", 
                headers=self.headers, 
                verify=False, 
                timeout=self.requestTimeout)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to read variable group. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, error=f'Failed to read variable group. Status code: {response.status_code}, Reason: {response.content}')
            
            # Return the grouped variables in a parsed dictionary
            results = self._parse_read_response(response.json())
            return self.APIResult(success=True, data=results, error=None)
              
        except Exception as e:
            self.logger.error(f"Exception occurred while reading a group: {repr(e)}")
            return self.APIResult(success=False,error=f"Exception occurred while reading a group: {repr(e)}")

    # ================================================================
    # Removes a variable group
    # ================================================================
    def remove_group(self, groupID: str) -> APIResult:
        """
        Removes a variable group.
        """
        try:

            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot remove group.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot remove group.')
            
            response = self.session.delete(
                f"{self.GROUPS_URL}/{groupID}",
                params={"sessionID": self.sessionID},
                headers=self.headers,
                verify=False,
                timeout=self.requestTimeout
            )

            # If code 204 returns then the group was removed successfully
            if response.status_code == 204:
                return self.APIResult(success=True)

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to remove variable group. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, error=f'Failed to remove variable group. Status code: {response.status_code}, Reason: {response.content}')
            
            # If everything else fails report that it failed
            return self.APIResult(success=False, error="Unable to remove the group.")

        except Exception as e:
            self.logger.error(f"Exception occurred while removing a group: {repr(e)}")
            return self.APIResult(success=False,error=f"Exception occurred while removing a group: {repr(e)}")

    # ================================================================
    # Generating Variable Dictionary if not generated
    # ================================================================
    @property
    def variables(self):
        """
        Returns the list of variables from the PLCnext API. If the variable dictionary is empty, it will attempt to build it.
        """
        # Get the variable list
        results = self._get_variable_list()

        # Ensure that the request to get the variable list succeeded, otherwise respond with blank
        if results.success:
            return results.data
        
        return []
    
    # ================================================================
    # Forcing a refresh of the variable dictionary
    # ================================================================
    def refresh_variables(self):
        """
        Refreshes the variable dictionary by forcing a rebuild of the variable list from the PLCnext API.
        """
        return self._get_variable_list(refresh=True)

    # ================================================================
    # Reading all variables
    # ===============================================================
    def readAllVariables(self):
        """
        Reads all variables from the PLCnext API by first refreshing the variable dictionary and then reading the values of all variables.
        """
        resp = self.refresh_variables()
        if resp.success:
            return self.read(resp.data)
        else:
            return resp

#########################
# INTERNAL FUNCTIONS
#########################
    # ================================================================
    # HTTP code handling for the PLCnext API
    # ================================================================
    def _validate_response(self, response) -> bool:
        """
        Validate an HTTP response and return True if valid.
        Returns False for handled HTTP errors.
        """
        self.logger.debug(f"API Status code: {response.status_code}")
        match response.status_code:

            case 200 | 201 | 204:
                return True

            case 400:
                self.logger.error(f"Bad Request (400): {response.text}")
                return False

            case 401:
                self.logger.error(f"Unauthorized (401): {response.text}")
                return False

            case 403:
                self.logger.error( f"Forbidden (403): {response.text}")
                return False

            case 404:
                self.logger.error(f"Not Found (404): {response.text}")
                return False

            case 409:
                self.logger.error(f"Conflict (409): {response.text}")
                return False

            case _:
                self.logger.error(f"Unexpected HTTP Status Code {response.status_code}: {response.text}")
                return False

    # ===============================================================
    # Session creation
    # ===============================================================   
    def _create_session(self):

        # Send a POST request to create a new session for the given stationID
        payload = f"stationID={self.stationID}&timeout={self.sessionTimeout}"
        response = self.session.post(
            self.SESSIONS_URL, 
            data=payload, 
            verify=False, 
            timeout=self.requestTimeout)

        # Validate the response
        if not self._validate_response(response):
            return False
        
        # If the response is successful, parse the JSON and set the sessionID
        self.logger.info(f'Session created successfully.')
        self.logger.debug(f"Session information: {response.json()}")
        self.sessionID = response.json()["id"]
        self.sessionCreatedTime = datetime.now(timezone.utc)
        self.logger.debug(f"Session created time: {self.sessionCreatedTime}")
        return True

    # ================================================================
    # Refresh timer
    # ================================================================
    def _session_needs_refresh(self) -> bool:

        if self.sessionCreatedTime is None:
            self.logger.debug(f"No created time.")
            return True

        elapsed = (datetime.now(timezone.utc) - self.sessionCreatedTime)
        self.logger.debug(f"Refresh needed status: {elapsed >= timedelta(milliseconds=self.sessionTimeout * 0.9)}")
        return elapsed >= timedelta(milliseconds=self.sessionTimeout * 0.9)

    # ================================================================
    # Session refresh
    # ================================================================
    def _refresh_session(self):

        # Check if sessionID is None, if so, log an error and return False
        if not self.sessionID:
            self.logger.error(f'Station ID is not set. Cannot refresh session.')
            return False
        
        # Send a PUT request to refresh the session for the given sessionID
        response = self.session.put(
            f'{self.SESSIONS_URL}/{self.sessionID}', 
            verify=False, 
            timeout=self.requestTimeout)

        # Validate the response
        if not self._validate_response(response):
            return False

        # If the response is successful, log the information and return True
        self.logger.info(f'Session created successfully.')
        self.sessionID = response.json()["sessionID"]
        self.logger.debug(f"Refresh session data: {response.json()}")
        self.sessionCreatedTime = datetime.now(timezone.utc)
        self.logger.debug(f"Created session time: {self.sessionCreatedTime}")
        return True
        

    # ================================================================
    # Session search
    # ================================================================
    def _find_session(self):

        # Check if a session already exists for the given stationID
        response = self.session.get(
            self.SESSIONS_URL, 
            verify=False, 
            timeout=self.requestTimeout)

        # Validate the response
        if not self._validate_response(response):
            return False

        # If the response is successful, parse the JSON and check for a session with the given stationID
        sessions = response.json()["sessions"]
        self.logger.debug(f"Sessions: {sessions}")
        # Loop through the sessions to find a match for the stationID
        for session in sessions:
            # If a session with the given stationID is found, set the sessionID and return True
            if session['stationID'] == self.stationID:
                self.sessionID = session['id']
                self.sessionCreatedTime = datetime.fromtimestamp(int(session["createdTimestamp"]) / 1000, tz=timezone.utc)
                self.logger.info(f'Session found for station ID {self.stationID}.')
                return True
            
        # If no session with the given stationID is not found, log the information and return False  
        self.logger.info(f'No session found for station ID {self.stationID}.')
        return False

    # ================================================================
    # Authentication (if applicable)
    # ================================================================
    def _authenticate(self):
        try:
            # Define the payload for the authentication request and request the auth token from the PLCnext API
            payload = {"scope": "variables"}
            authToken = self.session.post(
                f'{self.AUTH_URL}/auth-token', 
                data=json.dumps(payload), 
                verify=False, 
                timeout=self.requestTimeout)

            self.logger.debug(f"Auth token response: {authToken.json()}")

            # Validate the response
            if not self._validate_response(authToken):
                return False

            # Define the payload for the access token request and request the access token from the PLCnext API
            payload = {"code": authToken.json()['code'], "grant_type": "authorization_code", "username": self.username, "password": self.password}
            accessToken = self.session.post(
                f'{self.AUTH_URL}/access-token', 
                data=json.dumps(payload), 
                verify=False, 
                timeout=self.requestTimeout)

            self.logger.debug(f"Access token response: {accessToken.json()}")

            # Validate the response
            if not self._validate_response(accessToken):
                return False

            # If the response is successful, parse the JSON and set the headers for future requests
            self.headers = {"Authorization": accessToken.json()['access_token']}

            # Ensure that the authentication token is not empty before returning True
            if self.headers['Authorization'] ==   '':
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f'Exception on API authentication token handle: {e}')
            return False

    # ================================================================
    # Variable dictionary management
    # ================================================================
    def _get_variable_list(self, refresh=False):
        try:
            
            # Return the current dictionary if it exists and refresh is not requested
            if self.variableDict and not refresh:
                return self.APIResult(success=True, data=self.variableDict, error=None)
            
            # If the variable dictionary is empty or refresh is requested, ensure a valid connection to the PLCnext API
            connect_result = self.connect()
            if not connect_result.success:
                self.logger.error(f'Failed to connect to PLCnext API. Cannot build variable dictionary.')
                return self.APIResult(success=False, data=None, error=f'Failed to connect to PLCnext API. Cannot build variable dictionary.')

            # Request the variable dictionary from the PLCnext API and parse the response
            response = self.session.get(
                self.DICTIONARY_URL, 
                headers=self.headers, 
                verify=False, 
                timeout=self.requestTimeout)

            self.logger.debug(f"Variable list respose: {response.json()}")

            # Validate the response and log an error if the request fails
            if not self._validate_response(response):
                self.logger.error(f'Failed to retrieve variable dictionary. Status code: {response.status_code}, Reason: {response.content}')
                return self.APIResult(success=False, data=None, error=f'Failed to retrieve variable dictionary. Status code: {response.status_code}, Reason: {response.content}')

            # Parse the JSON response content into a dictionary
            dictionary = response.json()

            # Remove the prefix "Arp.Plc.Eclr/" from each variable name in the dictionary and store it in self.variableDict
            self.variableDict = [key.removeprefix(self.PATH_PREFIX) for key in dictionary["HmiVariables2"]]

            return self.APIResult(success=True, data=self.variableDict, error=None)

        except Exception as e:
            self.logger.error(f'Failed to build variable dictionary: {repr(e)}')
            return self.APIResult(success=False, data=None, error=f'Failed to build variable dictionary: {repr(e)}')


    def _create_read_url(self, variables: list) -> str | None:
        """
        Creates a read URL for the given list of variables.
        """
        try:

            # Build the read string for the given list of variables
            read_str = ",".join(variables)
            return (f"{self.VARIABLES_URL}"
                    f"?pathPrefix={self.PATH_PREFIX}"
                    f"&paths={read_str}")

        except Exception as e:
            self.logger.error(f'Error occurred while creating read URL: {repr(e)}')
            return None

    def _parse_read_response(self, payload: dict) -> dict | None:
        """
        Converts a read response payload into a dictionary of variable
        names and their corresponding values, types, and errors.
        """
        try:

            result = {}

            for variable in payload["variables"]:

                name = variable["path"].removeprefix(self.PATH_PREFIX)
                result[name] = {
                    "value": variable.get("value"),
                    "type": variable.get("type"),
                    "error": variable.get("error", {}).get("reason")
                }

            return result

        except Exception as e:
            self.logger.error(f'Error occurred while parsing read response: {repr(e)}')
            return None