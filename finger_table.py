import bisect
import sys
import json

filename = "dht.json"

f = open(filename)
data = json.loads(f.read())

hm = data["dht"]
hm.sort(key= lambda x:x["hash"])

pair = {}

for key in hm:
    pair[key["hash"]] = key

arr = []

bits = 8

for tup in hm:
    arr.append(tup["hash"])

finger_tables = {}

for i in range(len(arr)):
    temp = {}

    for j in range(1,bits+1):
        num = (arr[i] + 2**(j-1)) % (2**bits)

        idx = bisect.bisect_left(arr,num)

        if idx == len(arr):
            idx = 0

        temp[j] = pair[arr[idx]]


    finger_tables[arr[i]] = temp


with open('fingertable.json', 'w') as f:
    json.dump(finger_tables, f)