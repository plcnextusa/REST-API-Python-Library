# Libraries to import
import REST
import time

loopcount = 0
start_time = time.time()
# Initialize the API
plc = REST.API(credentials=None, logfileSize=1000000, logfileBackupCount=1, logfileNameLocation='/opt/plcnext/project.log')

# Multi-Read
loopcount = 0
start_time = time.time()
while loopcount<=500:
    plc.readAll()
    loopcount+=1
totalTime = time.time() - start_time
print("Read All report:")
print("--- %s seconds ---" % (totalTime))
print(f"Requests per second: {500/totalTime}")
print(f"Average request time: {1/(500/totalTime)}")

# Single-Read
loopcount = 0
start_time = time.time()
while loopcount<=500:
    plc.read(['testString'])
    loopcount+=1
totalTime = time.time() - start_time
print("Read Single report:")
print("--- %s seconds ---" % (totalTime))
print(f"Requests per second: {500/totalTime}")
print(f"Average request time: {1/(500/totalTime)}")

# Single-Write
loopcount = 0
start_time = time.time()
while loopcount<=500:
    plc.write([{'name': 'loopcount', 'value': loopcount}])
    loopcount+=1
totalTime = time.time() - start_time
print("Write Single report:")
print("--- %s seconds ---" % (totalTime))
print(f"Requests per second: {500/totalTime}")
print(f"Average request time: {1/(500/totalTime)}")