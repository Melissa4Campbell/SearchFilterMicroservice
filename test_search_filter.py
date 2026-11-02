# test_search_filter.py
# Test program for the Search/Filter microservice.
# It sends requests to port 5561 and prints each reply.

import json
import time

import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5561")

RECORDS = [
    {"id": 1, "name": "Aria", "tags": ["elf"], "date": "03/15/2026", "notes": "Fears dragons"},
    {"id": 2, "name": "Brom", "tags": ["dwarf"], "date": "04/02/2026", "notes": "Loves ale"},
    {"id": 3, "name": "Cael", "tags": ["elfin", "mage"], "date": "03/28/2026", "notes": "Studies stars"},
]


def describe_request(request):
    """Make a short summary of a request so it is easy to read."""
    parts = ["action = " + str(request.get("action"))]
    for key in ("term", "tag", "start_date", "end_date"):
        if key in request:
            parts.append(key + " = " + str(request[key]))
    if "records" in request:
        parts.append(str(len(request["records"])) + " records")
    return ", ".join(parts)


def describe_reply(reply):
    """Make a short summary of a reply so it is easy to read."""
    if reply["status"] == "ok":
        names = [record.get("name") for record in reply["results"]]
        return "status = ok, count = " + str(reply["count"]) + ", names = " + str(names[:5])
    return "status = error, message = " + reply["message"]


def ask(request):
    """Send one request, wait for the reply, and return it as a dictionary."""
    print("Sending:  " + describe_request(request))
    socket.send_string(json.dumps(request))
    reply = json.loads(socket.recv_string())
    print("Received: " + describe_reply(reply))
    return reply


def check(name, passed):
    """Print PASS or FAIL for one test."""
    print(("PASS: " if passed else "FAIL: ") + name)
    print()


print("Test 1: an unknown action")
reply = ask({"action": "banana", "records": RECORDS})
check("unknown action gives an error", reply["status"] == "error")

print("Test 2: search for dragon")
reply = ask({"action": "search", "records": RECORDS, "term": "dragon"})
check("search finds one record", reply["status"] == "ok" and reply["count"] == 1
      and reply["results"][0]["name"] == "Aria")

print("Test 3: search for a word nobody has")
reply = ask({"action": "search", "records": RECORDS, "term": "zzz"})
check("search with no match gives 0", reply["status"] == "ok" and reply["count"] == 0)

print("Test 4: filter by the tag elf")
reply = ask({"action": "filter_tag", "records": RECORDS, "tag": "elf"})
check("filter_tag returns only elf", reply["status"] == "ok" and reply["count"] == 1
      and reply["results"][0]["name"] == "Aria")

print("Test 5: filter by tag with no tag sent")
reply = ask({"action": "filter_tag", "records": RECORDS})
check("missing tag gives an error that mentions tag",
      reply["status"] == "error" and "tag" in reply["message"])

print("Test 6: filter by dates in March")
reply = ask({"action": "filter_date", "records": RECORDS,
             "start_date": "03/01/2026", "end_date": "03/31/2026"})
check("filter_date returns the two March records", reply["status"] == "ok" and reply["count"] == 2
      and reply["results"][0]["name"] == "Aria" and reply["results"][1]["name"] == "Cael")

print("Test 7: a start date after the end date")
reply = ask({"action": "filter_date", "records": RECORDS,
             "start_date": "04/01/2026", "end_date": "03/01/2026"})
check("start date after end date gives the right error",
      reply["status"] == "error" and reply["message"] == "start_date must not be after end_date")

print("Test 8: a good request right after an error")
reply = ask({"action": "banana", "records": RECORDS})
reply = ask({"action": "search", "records": RECORDS, "term": "ale"})
check("a good request right after an error still works", reply["status"] == "ok" and reply["count"] == 1)

print("Test 9: speed with 1000 records")
big = [{"id": i, "name": "Person " + str(i), "tags": ["x"], "date": "03/15/2026",
        "notes": "note " + str(i)} for i in range(1000)]
started = time.time()
reply = ask({"action": "search", "records": big, "term": "999"})
seconds = time.time() - started
print("The reply took " + str(round(seconds, 3)) + " seconds.")
check("1000 records answered in 1 second or less", reply["status"] == "ok" and seconds <= 1)