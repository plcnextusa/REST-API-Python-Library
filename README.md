# PLCnext API Library for Python

A lightweight Python wrapper for the PLCnext REST API that provides automatic session management, authentication support, variable reads and writes, variable dictionary caching, and native PLCnext variable group support.

---

# Features

- Automatic session discovery
- Automatic session creation
- Automatic session refresh
- Optional user authentication
- Read one or more variables
- Write one or more variables
- Read all variables
- Cached variable dictionary
- Create PLCnext variable groups
- Read PLCnext variable groups
- List active PLCnext groups
- Remove PLCnext variable groups
- Structured API result objects
- Native Python logging support

---

# Installation

## Requirements

- Python 3.7+
- PLCnext Runtime with REST API enabled

Install dependencies:

```bash
pip install requests
```

---

# Importing

```python
from plcnext_api import PLCnextAPI
```

---

# Creating an API Instance

```python
plc = PLCnextAPI(
    ip="192.168.1.10",
    requestTimeout=5,
    sessionTimeout=10800000,
    stationID="1"
)
```

## Parameters (optional)

### `ip`

PLC IP address. If connecting locally, this parameter does not need to be used.

Default:

```python
ip="localhost"
```

### `requestTimeout`

HTTP request timeout in seconds.

Default:

```python
requestTimeout=5
```

### `sessionTimeout`

Requested PLCnext session timeout in milliseconds.

Default:

```python
sessionTimeout=10800000
```

### `stationID`

PLCnext station ID for session management. This should be unique for each connection.

Default:

```python
stationID="1"
```

---

# Connecting

The library automatically:

- Authenticates (if credentials are supplied)
- Discovers existing sessions
- Creates sessions when necessary
- Refreshes sessions before timeout

## Anonymous Access (if ehMI Authentication is disabled)

```python
result = plc.connect()

if not result.success:
    print(result.error)
```

## Authenticated Access (eHMI Authenticaton enabled)

```python
result = plc.connect(
    username="admin",
    password="password"
)

if not result.success:
    print(result.error)
```

---

# APIResult

Every public API function returns an `APIResult`.

## Structure

```python
APIResult(
    success=True,
    data=None,
    error=None
)
```

## Example

```python
result = plc.read(["MotorSpeed"])

if result.success:
    print(result.data)
else:
    print(result.error)
```

---

# Reading Variables

## Read One Variable

```python

result = plc.read(["MotorSpeed"])

# OR

variable = ["MotorSpeed"]
result = plc.read(variable)
```

### Example Response

```python
{
    "MotorSpeed": {
        "value": 1500,
        "type": None,
        "error": None
    }
}
```

Type is only used when doing a group read. Error indicates if the variable does not exist, or there was an issue returning a value. Assume the data is stale if error is true.

---

## Read Multiple Variables

```python
result = plc.read(["MotorSpeed", "MotorRun", "CycleCount"])

# OR

variables = ["MotorSpeed", "MotorRun", "CycleCount"]
result = plc.read(variables)
```

### Example Response

```python
{
    "MotorSpeed": {
        "value": 1500,
        "type": None,
        "error": None
    },
    "MotorRun": {
        "value": True,
        "type": None,
        "error": None
    },
    "CycleCount": {
        "value": 100,
        "type": None,
        "error": None
    }
}
```

Type is only used when doing a group read. Error indicates if the variable does not exist, or there was an issue returning a value. Assume the data is stale if error is true.

---

# Writing Variables

## Write One Variable

```python
result = plc.write({"MotorSpeed": 1500})

# OR

variables["MotorSpeed"] = 1500
result = plc.write(variables)
```

---

## Write Multiple Variables

```python
result = plc.write({"MotorSpeed": 1500, "MotorRun": True, "CycleCount": 100})

# OR

variables["MotorSpeed"] = 1500
variables["MotorRun"] = True
variables["CycleCount"] = 100
result = plc.write(variables)
```

---

# Variable Dictionary

The variable dictionary is automatically downloaded and cached.

---

## Get Available Variables

```python
variables = plc.variables

# Print out the list of variables
for variable in variables:
    print(variable)
```

### Example Output

```python
[
    "MotorSpeed",
    "MotorRun",
    "CycleCount"
]
```

---

## Refresh Variable Dictionary

```python
result = plc.refresh_variables()

# Ensure the request was successful and print the output
if result.success:
    print(result.data)
```

---

# Read All Variables

Reads every variable discovered in the cached variable dictionary.

```python
result = plc.readAllVariables()

# Ensure the request was successful and print the output
if result.success:
    print(result.data)
```

### Example Response

```python
{
    "MotorSpeed": {
        "value": 1500,
        "type": None,
        "error": None
    },
    "MotorRun": {
        "value": True,
        "type": None,
        "error": None
    }
}
```

---

# PLCnext Variable Groups

Variable groups allow multiple variables to be registered into a group on the PLC and retrieved using a single request.

This can significantly improve performance when repeatedly requesting the same variables.

---

# List Registered Groups

Returns all active PLCnext groups.

```python
result = plc.list_groups()

if result.success:
    for group in result.data:
        print(group["id"])
```

### Example Response

```python
[
    {
        "id": "g1527984639",
        "variableCount": 10,
        "uri": "https://plc/_pxc_api/api/groups/g1527984639",
        "createdTimestamp": "1786640140005",
        "usedTimestamp": "1786640140005",
        "accessCount": 25,
        "totalTimeAverage": 1.2,
        "totalTimeMax": 5.6,
        "ehmiTimeAverage": 0.8,
        "ehmiTimeMax": 2.1,
        "gdsTimeAverage": 0.4,
        "gdsTimeMax": 1.1
    }
]
```

---

# Create a Group

Create a PLCnext variable group.

```python
result = plc.create_group(["MotorSpeed", "MotorRun", "CycleCount"])

# OR

group = ["MotorSpeed", "MotorRun", "CycleCount"]
result = plc.create_group(group)
```

Retrieve the Group ID:

```python
groupID = result.data
```

Example:

```python
print(groupID)
```

Output:

```text
g2798617204
```

Keep this group ID for the request!

---

# Array Indexing Support for Groups

PLCnext array indexing syntax is supported for groups.

## Single Element

```python
result = plc.create_group(
    [
        "PartArray[2]"
    ]
)
```

## Multiple Elements

```python
result = plc.create_group(
    [
        "PartArray[2;4]"
    ]
)
```

## Range

```python
result = plc.create_group(
    [
        "PartArray[6-8]"
    ]
)
```

## Mixed Selections

```python
result = plc.create_group(
    [
        "PartArray[2;4;6-8]"
    ]
)
```

---

# Reading a Group

Read the values contained within a previously registered PLCnext group.

```python
result = plc.read_group(groupID)
```

### Example Response

```python
{
    "MotorSpeed": {
        "value": 1500,
        "type": "INT",
        "error": None
    },
    "MotorRun": {
        "value": True,
        "type": "BOOL",
        "error": None
    },
    "CycleCount": {
        "value": 100,
        "type": "INT",
        "error": None
    }
}
```

Group reads include PLC data types when available.

---

# Removing a Group

Remove a previously registered group.

```python
result = plc.remove_group(groupID)

if result.success:
    print("Group removed successfully.")
```

---

# Logging

The library uses Python's built-in logging module.

---

## Enable Informational Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
```

### Example Output

```text
2026-08-13 17:00:00 - INFO - Authentication succeeded.
2026-08-13 17:00:00 - INFO - Session found for station ID 1.
2026-08-13 17:00:00 - INFO - Session ID active.
```

---

## Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
```

This includes:

- Session discovery details
- Session creation details
- Authentication responses
- API status codes
- Variable dictionary responses

---

# Performance Benchmark Examples

## Read All Variables

```python
import time

start_time = time.time()

for _ in range(500):
    plc.readAllVariables()

total_time = time.time() - start_time

print(f"Requests/sec: {500 / total_time}")
print(f"Average request time: {total_time / 500}")
```

---

## Read Single Variable

```python
import time

start_time = time.time()

for _ in range(500):
    plc.read(["testString"])

total_time = time.time() - start_time

print(f"Requests/sec: {500 / total_time}")
print(f"Average request time: {total_time / 500}")
```

---

## Write Single Variable

```python
import time

start_time = time.time()

for i in range(500):
    plc.write(
        {
            "loopcount": i
        }
    )

total_time = time.time() - start_time

print(f"Requests/sec: {500 / total_time}")
print(f"Average request time: {total_time / 500}")
```

---

## Read Variable Group

```python
group_result = plc.create_group(
    [
        "testString"
    ]
)

groupID = group_result.data

start_time = time.time()

for _ in range(500):
    plc.read_group(groupID)

total_time = time.time() - start_time

print(f"Requests/sec: {500 / total_time}")
print(f"Average request time: {total_time / 500}")

plc.remove_group(groupID)
```

---

# Complete Example

```python
from plcnext_api import PLCnextAPI

plc = PLCnextAPI(
    ip="192.168.1.10"
)

result = plc.connect()

if not result.success:
    raise RuntimeError(result.error)

result = plc.read(
    [
        "MotorSpeed",
        "MotorRun"
    ]
)

print(result.data)

plc.write(
    {
        "MotorRun": True
    }
)

group = plc.create_group(
    [
        "MotorSpeed",
        "MotorRun"
    ]
)

groupID = group.data

result = plc.read_group(groupID)

print(result.data)

plc.remove_group(groupID)
```

---

# Public API Reference

```python
connect(username=None, password=None)

read(variables: list[str])

write(variables: dict)

@property
variables

refresh_variables()

readAllVariables()

list_groups()

create_group(variables: list[str])

read_group(groupID: str)

remove_group(groupID: str)
```

---


# License

MIT License

Copyright © 2026 PLCnextAPI Contributors.
