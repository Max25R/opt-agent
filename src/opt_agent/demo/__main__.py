"""python -m opt_agent.demo [--host HOST] [--port PORT]: serve the demo (app.py) with uvicorn.
Examples mode unless OPT_AGENT_LIVE=1 (then the key in .env, or an exported one)."""

import argparse

import uvicorn

from opt_agent.demo.app import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the opt-agent demo.")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside Docker")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
