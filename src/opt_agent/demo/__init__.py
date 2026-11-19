"""The demo: the pipeline (agent.run) behind one web page and a small JSON API.

- pipeline.py: the demo's fixed settings and solve(), shared by the app and by
  scripts/cache_examples.py, so a cached example replays exactly the requests it was cached
  with; to_response() turns a result into the JSON the page shows.
- examples.py: four original example problems, each with a hand-checked answer.
- app.py: the FastAPI app (GET /, /health, /examples; POST /solve) and its two modes.
- page.html: the page, served as it is (no build step); scripts/static_demo.py also
  builds it, with the app's responses, into the static site on GitHub Pages.
- replies/: the examples' cached replies, written by scripts/cache_examples.py.
"""
