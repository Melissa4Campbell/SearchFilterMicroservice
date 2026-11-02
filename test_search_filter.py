# test_search_filter.py
# Test program for the Search/Filter microservice.
# It sends requests to port 5561 and prints each reply.

import json

import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5561")

RECORDS = [
    {"id": 1, "name": "Aria", "tags": ["elf"], "date": "03/15/2026", "notes": "Fears dragons"},
    {"id": 2, "name": "Brom", "tags": ["dwarf"], "date": "04/02/2026", "notes": "Loves ale"},
    {"id": 3, "name": "Cael", "tags": ["elfin", "mage"], "date": "03/28/2026", "notes": "Studies stars"},
]


def ask(request):
    """Send one request, wait for the reply, and return it as a dictionary."""
    print("Sending: " + json.dumps(request))
    socket.send_string(json.dumps(request))
    reply = json.loads(socket.recv_string())
    print("Received: " + json.dumps(reply))
    return reply


def check(name, passed):
    """Print PASS or FAIL for one test."""
    print(("PASS: " if passed else "FAIL: ") + name)
    print()


# Test 1: an unknown action should give an error
reply = ask({"action": "banana", "records": RECORDS})
check("unknown action gives an error", reply["status"] == "error")



# Test 2: search finds only the matching record
reply = ask({"action": "search", "records": RECORDS, "term": "dragon"})
check("search finds one record", reply["status"] == "ok" and reply["count"] == 1
      and reply["results"][0]["name"] == "Aria")

# Test 3: search with no match gives an empty list
reply = ask({"action": "search", "records": RECORDS, "term": "zzz"})
check("search with no match gives 0", reply["status"] == "ok" and reply["count"] == 0)



# Test 4: filter by tag returns only the exact tag
reply = ask({"action": "filter_tag", "records": RECORDS, "tag": "elf"})
check("filter_tag returns only elf", reply["status"] == "ok" and reply["count"] == 1
      and reply["results"][0]["name"] == "Aria")

# Test 5: filter by tag with the tag missing gives a clear error
reply = ask({"action": "filter_tag", "records": RECORDS})
check("missing tag gives an error that mentions tag",
      reply["status"] == "error" and "tag" in reply["message"])



# Test 6: filter by date returns only records on or between the two dates
reply = ask({"action": "filter_date", "records": RECORDS,
             "start_date": "03/01/2026", "end_date": "03/31/2026"})
check("filter_date returns the two March records", reply["status"] == "ok" and reply["count"] == 2
      and reply["results"][0]["name"] == "Aria" and reply["results"][1]["name"] == "Cael")

# Test 7: a start date after the end date gives a clear error
reply = ask({"action": "filter_date", "records": RECORDS,
             "start_date": "04/01/2026", "end_date": "03/01/2026"})
check("start date after end date gives the right error",
      reply["status"] == "error" and reply["message"] == "start_date must not be after end_date")

# Test 8: the microservice keeps working after an error
reply = ask({"action": "banana", "records": RECORDS})
check("unknown action gives an error", reply["status"] == "error")
reply = ask({"action": "search", "records": RECORDS, "term": "ale"})
check("a good request right after an error still works", reply["status"] == "ok" and reply["count"] == 1)

# Test 9: speed with 1000 records
import time

big = [{"id": i, "name": "Person " + str(i), "tags": ["x"], "date": "03/15/2026",
        "notes": "note " + str(i)} for i in range(1000)]
started = time.time()
socket.send_string(json.dumps({"action": "search", "records": big, "term": "999"}))
reply = json.loads(socket.recv_string())
seconds = time.time() - started
print("Sent a request with 1000 records. The reply took " + str(round(seconds, 3)) + " seconds.")
check("1000 records answered in 1 second or less", reply["status"] == "ok" and seconds <= 1)