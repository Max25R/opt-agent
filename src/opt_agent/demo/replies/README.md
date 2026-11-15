# The demo examples' cached replies

One JSON file per Claude call (`api.Cache`: the request, the response, and how the call
went), written by `scripts/cache_examples.py` in the owner's terminal (a paid run) and
replayed by the demo's examples mode with no key. Never edit these by hand: a reply that
doesn't match its request's cache key is simply not found.
