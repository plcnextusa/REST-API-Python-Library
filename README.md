# REST-API-Python-Library

This library is for communicating to the PLCnext Engineer REST API server. This code is only meant to run locally on a PLCnext target, not on any remote machines.

Examples are provided for authentication and non-authentication methods, with a PLCnext Engineer project included.

## Library functions
## Initializing the library
The below function is used to initialize the library and start communication to the REST API server. This function also handles the authentication token as well as creating a HTTP session. The function output is the variable used to read or write any variables.
#### NOTE: If credentails are being used and the library does not have them, errors will flood the logfile but the code will still run. Ensure that you have the correct option selected for authentication!
Example:
```
plc = REST.API()
```
For this function there are 4 parameters:
1. credentials: If authentication is being used, enter the username and password within a list.
```
credentials = ['admin','private']
```
If authentication is not being used, set credentails to None or do not use the credentails parameter.\
Example:
```
plc = REST.API(credentails = None)

OR

plc = REST.API()

```
2. logfileSize: This is the size of the logfile to create for library related issues. The default is 1MB, and the unit for this parameter is bytes.\
Example:
```
plc = REST.API(logfileSize=1000000)
```
3. logfileBackupCount: This is the total number of file backups for the logfile. The default is 1 backup, meaning there is 2MB of logs available. The default is 1.\
Example:
```
plc = REST.API(logfileBackupCount=1)
```
4. logfileNameLocation: This is the name of the logfile and the location to store the logfile. This parameter is all one string, with the full path of the logfile.\
Example:
```
plc = REST.API(logfileNameLocation='/opt/plcnext/project.log'
```
Each of these parameters do not have to be used when initializing the library, but are optional based on your application.\

## Reading tags
There are 2 functions to read tags from the REST API server:\
The function below will read tags specified in its parameter varaibles.
```
plc = REST.API()
plc.read()
```
1. variables: This parameter is a list of all the variables that would need to be read from the REST API server. The variable is formatted as a list with each name as a string. The output from the function will be a list containing the name and the value of the variable.\
Example execution:
```
plc = REST.API()
vars = ['testVariable1','testVariable2','testVariable3']
plc.read(variables = vars)
```
Example output:
```
[{'name': 'testBool', 'value': False},{'name': 'testInt', 'value': 15}]
```
The function below will read all tags that are available from the REST API server. The output from the function will be a list containing the name and the value of the variable.
#### NOTE: The taglist is only read one time. If a program update occurs, restart your program to get the latest tag list.
```
readAll()
```
Example output:
```
[{'name': 'testBool', 'value': False},{'name': 'testInt', 'value': 15}]
```

## Writing tags
The function below will write tags specified in its parameter variables.
```
plc = REST.API()
plc.write()
```
1. varaibles: This parameter is a list of allof the variables that would need to be written to the REST API server. The variable is formatted as a list with the name and value of each tag. The output of the function will indicate if the write was a success or failure.\
Example:
```
plc = REST.API()
vars = [{'name': 'testInt', 'value': 234},{'name': 'testBool', 'value': True}]
plc.write(variables=vars)
```
