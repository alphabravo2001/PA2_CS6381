###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the publisher middleware code
#
# Created: Spring 2023
#
###############################################

# This file contains any declarations that are common to all middleware entities

# For now we do not have anything here but you can add enumerated constants for
# the role we are playing and any other common things that we need across
# all our middleware objects. Make sure then to import this file in those files once
# some content is added here that is needed by others.

import random # random number generation
import hashlib  # for the secure hash library
import argparse # argument parsing
import json # for JSON
import logging # for logging. Use it in place of print statements.

bits_hash = 8

def chord(target, cur, fingerhm, arr):
    topichash = hashtopic(target)

    cpnode = search(topichash, cur, fingerhm, arr)

    return fingerhm[cpnode][0]["hash"]


def search(target,cur,hm,arr):

    if target > cur and target <= hm[cur][0]["hash"]:
        return hm[cur][0]["hash"]

    else:
        newcur = closestpreceding(cur, arr)
        return search(target, newcur, hm, arr)


def closestpreceding(cur,arr):

    if cur > arr[-1]:
        return arr[0]

    else:
        for hash in arr:
            if cur < hash:
                return hash


def hashtopic(hash):
    # first get the digest from hashlib and then take the desired number of bytes from the
    # lower end of the 256 bits hash. Big or little endian does not matter.
    hash_digest = hashlib.sha256(bytes(id, "utf-8")).digest()  # this is how we get the digest or hash value
    # figure out how many bytes to retrieve
    num_bytes = int(bits_hash / 8)  # otherwise we get float which we cannot use below
    hash_val = int.from_bytes(hash_digest[:num_bytes], "big")  # take lower N number of bytes

    return hash_val