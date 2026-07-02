# Simple load-test script that hits the season recap page repeatedly.
import urllib.request
import time

url = "http://localhost:5000/season-recap"
n = 100
start = time.time()

for i in range(n):
    urllib.request.urlopen(url)

total = time.time() - start
print(f"Total time: {total:.2f}s")
print(f"Requests per second: {n/total:.2f} req/s")
print(f"Avg time per request: {total/n*1000:.2f}ms")