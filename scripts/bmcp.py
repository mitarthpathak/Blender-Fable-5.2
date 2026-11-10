#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.26,<2"]
# ///
"""Command-line client for the Blender MCP server.

Starts the same server `.mcp.json` registers (scripts/mcp-server.sh), speaks
MCP to it over stdio, and prints the result. Useful for smoke tests, and for
driving Blender from a session whose tool list was built before the server was
registered.

    scripts/bmcp.py tools
    scripts/bmcp.py call get_scene_info
    scripts/bmcp.py call execute_blender_code '{"code": "import bpy; print(bpy.app.version_string)"}'
    scripts/bmcp.py code path/to/script.py          # run a file inside Blender
    scripts/bmcp.py --out shot.png look             # save what the `look` tool sees

Images in a result are written to --out (default .scratch/bmcp.png, with a
numbered sibling per extra image) and the path is printed instead of the bytes.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

import subprocess

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SCRIPTS = Path(__file__).resolve().parent
SERVER = SCRIPTS / "mcp-server.sh"


def _image_path(out: Path, index: int, mime: str) -> Path:
    suffix = "." + (mime.split("/")[-1] if "/" in mime else "png").replace("jpeg", "jpg")
    base = out if out.suffix else out.with_suffix(suffix)
    return base if index == 0 else base.with_name(f"{base.stem}-{index}{base.suffix}")


def _print_result(result, out: Path) -> int:
    images = 0
    for item in result.content:
        if item.type == "text":
            print(item.text)
        elif item.type == "image":
            path = _image_path(out, images, item.mimeType)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(item.data))
            print(f"[image saved: {path}]")
            images += 1
        else:
            print(f"[{item.type} content omitted]")
    return 1 if result.isError else 0


async def _run(args: argparse.Namespace) -> int:
    # Pass the whole environment, as Claude Code does: the SDK's default is a
    # short allowlist that drops proxy and certificate settings.
    params = StdioServerParameters(command=str(SERVER), args=[], env=dict(os.environ))
    # The server's own logging goes to stderr; keep it out of the way unless asked.
    errlog = sys.stderr if args.verbose else open("/dev/null", "w")
    async with stdio_client(params, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if args.command == "tools":
                for tool in (await session.list_tools()).tools:
                    summary = (tool.description or "").strip().splitlines()
                    print(f"{tool.name}: {summary[0] if summary else ''}")
                    if args.schema:
                        print(json.dumps(tool.inputSchema, indent=2))
                return 0

            if args.command == "code":
                if args.file == "-":
                    source = sys.stdin.read()
                else:
                    # Run the file by path so __file__ is set and tracebacks name it.
                    path = Path(args.file).resolve(strict=True)
                    source = f"import runpy\nrunpy.run_path({str(path)!r}, run_name='__main__')\n"
                name, arguments = "execute_blender_code", {"code": source}
            elif args.command == "look":
                name, arguments = "look", json.loads(args.arguments or "{}")
            else:
                name, arguments = args.tool, json.loads(args.arguments or "{}")

            result = await session.call_tool(name, arguments)
            return _print_result(result, Path(args.out))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="show the MCP server's log output")
    parser.add_argument("--out", default=".scratch/bmcp.png", help="where to save images returned by a tool")
    sub = parser.add_subparsers(dest="command", required=True)

    tools = sub.add_parser("tools", help="list the server's tools")
    tools.add_argument("--schema", action="store_true", help="also print each tool's input schema")

    call = sub.add_parser("call", help="call a tool by name")
    call.add_argument("tool")
    call.add_argument("arguments", nargs="?", help="tool arguments as a JSON object")

    code = sub.add_parser("code", help="run a Python file inside Blender ('-' reads stdin)")
    code.add_argument("file")

    look = sub.add_parser("look", help="call the `look` tool and save the image")
    look.add_argument("arguments", nargs="?", help="tool arguments as a JSON object")

    args = parser.parse_args()
    if args.command != "tools":
        # The server starts Blender in the background and connects lazily; a
        # one-shot command would race that, so wait for Blender here first.
        up = subprocess.run([str(SCRIPTS / "blender-up.sh")], stdout=sys.stderr,
                            stderr=sys.stderr if args.verbose else subprocess.PIPE, text=True)
        if up.returncode != 0:
            sys.stderr.write(up.stderr or "")
            return up.returncode
    try:
        return asyncio.run(_run(args))
    except BaseException as error:  # the SDK wraps failures in exception groups
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        if args.verbose:
            raise
        leaf = error
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        if isinstance(leaf, BrokenPipeError):  # output piped into `head` and the like
            return 0
        sys.stderr.write(f"bmcp: the MCP server failed: {leaf}\n"
                         "bmcp: run again with -v to see the server's own output\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
