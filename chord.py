import json

filename = "fingertable.json"
f = open(filename)
hm = json.loads(f.read())
arr = []

for key in hm:
    arr.append(key)

def search(target,cur,hm):

    newcur = None

    for key in range(hm[cur]):

        if key["hash"] == target:
            return hm[cur][key]

        elif not newcur:
            newcur = closestpreceding(cur)

    return search(target, newcur)


def closestpreceding(cur,arr):

    if cur > arr[-1]:
        return arr[0]

    else:
        for hash in arr:
            if cur < hash:
                return hash
