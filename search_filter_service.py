# search_filter_service.py
# Search/Filter microservice.
# It waits for one request at a time on port 5561 (ZeroMQ), then sends back one reply.

import json
from datetime import datetime

import zmq

PORT = 5561


def error_reply(message):
    """Build the reply used whenever something is wrong."""
    return {"status": "error", "message": message}


def ok_reply(results):
    """Build the reply used when everything worked."""
    return {"status": "ok", "count": len(results), "results": results}


def record_contains_term(record, term):
    """Return True if the term appears in any text field of the record.
    Upper or lower case does not matter."""
    term = term.lower()
    for value in record.values():
        if isinstance(value, str) and term in value.lower():
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and term in item.lower():
                    return True
    return False


def search(records, term):
    """Return only the records that contain the term."""
    return [r for r in records if isinstance(r, dict) and record_contains_term(r, term)]


def filter_by_tag(records, tag):
    """Return only the records whose tags list contains exactly this tag."""
    tag = tag.lower()
    results = []
    for record in records:
        if not isinstance(record, dict):
            continue
        tags = record.get("tags")
        if not isinstance(tags, list):
            continue
        lowered = [t.lower() for t in tags if isinstance(t, str)]
        if tag in lowered:
            results.append(record)
    return results


def filter_by_date(records, start, end):
    """Return only the records whose date is on or between start and end."""
    results = []
    for record in records:
        if not isinstance(record, dict):
            continue
        text = record.get("date")
        if not isinstance(text, str):
            continue
        try:
            when = datetime.strptime(text, "%m/%d/%Y")
        except ValueError:
            continue
        if start <= when <= end:
            results.append(record)
    return results

def handle_request(request):
    """Look at one request and return the reply (a dictionary)."""
    if not isinstance(request, dict):
        return error_reply("Request must be a JSON object")

    action = request.get("action")
    if action not in ("search", "filter_tag", "filter_date"):
        return error_reply("Unknown action: " + str(action))

    records = request.get("records")
    if not isinstance(records, list):
        return error_reply("records is required and must be a list")

    if action == "search":
        term = request.get("term")
        if not isinstance(term, str) or term == "":
            return error_reply("term is required for search")
        return ok_reply(search(records, term))

    if action == "filter_tag":
        tag = request.get("tag")
        if not isinstance(tag, str) or tag == "":
            return error_reply("tag is required for filter_tag")
        return ok_reply(filter_by_tag(records, tag))

    # The only action left is filter_date
    start_text = request.get("start_date")
    end_text = request.get("end_date")
    if not isinstance(start_text, str) or not isinstance(end_text, str):
        return error_reply("start_date and end_date are required for filter_date")
    try:
        start = datetime.strptime(start_text, "%m/%d/%Y")
        end = datetime.strptime(end_text, "%m/%d/%Y")
    except ValueError:
        return error_reply("start_date and end_date must be written as MM/DD/YYYY")
    if start > end:
        return error_reply("start_date must not be after end_date")
    return ok_reply(filter_by_date(records, start, end))


def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:" + str(PORT))
    print("Search/Filter microservice is running on port " + str(PORT))
    print("Press the Control key and the C key together to stop it.")

    try:
        while True:
            # Wait up to half a second for a request. This short wait is what
            # lets Control and C stop the program on Windows.
            if socket.poll(500) == 0:
                continue
            message = socket.recv_string()
            try:
                request = json.loads(message)
                reply = handle_request(request)
            except json.JSONDecodeError:
                reply = error_reply("Request must be valid JSON text")
            except Exception as problem:
                reply = error_reply("Something went wrong: " + str(problem))
            socket.send_string(json.dumps(reply))
    except KeyboardInterrupt:
        print("Search/Filter microservice stopped.")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    main()