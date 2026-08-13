import logging
import time
from plcnext_api import PLCnextAPI

# Set the logger to print to console
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize the API
plc = PLCnextAPI(ip="localhost",requestTimeout=5,sessionTimeout=10800000,stationID="1")

# Ensure connection exists before benchmarking
result = plc.connect()

if not result.success:
    raise RuntimeError(result.error)

# ============================================================
# Read All Variables
# ============================================================

loopcount = 0
start_time = time.time()

while loopcount <= 500:
    plc.readAllVariables()
    loopcount += 1

totalTime = time.time() - start_time

print("Read All report:")
print(f"--- {totalTime} seconds ---")
print(f"Requests per second: {500 / totalTime}")
print(f"Average request time: {totalTime / 500}")

# ============================================================
# Read Single Variable
# ============================================================

loopcount = 0
start_time = time.time()

while loopcount <= 500:
    plc.read(["testString"])
    loopcount += 1

totalTime = time.time() - start_time

print("Read Single report:")
print(f"--- {totalTime} seconds ---")
print(f"Requests per second: {500 / totalTime}")
print(f"Average request time: {totalTime / 500}")

# ============================================================
# Write Single Variable
# ============================================================

loopcount = 0
start_time = time.time()

while loopcount <= 500:
    plc.write({
        "loopcount": loopcount
    })
    loopcount += 1

totalTime = time.time() - start_time

print("Write Single report:")
print(f"--- {totalTime} seconds ---")
print(f"Requests per second: {500 / totalTime}")
print(f"Average request time: {totalTime / 500}")