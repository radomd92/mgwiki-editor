"""Trusted administration, local broker client, and stdio MCP adapter. Never auto-deploys."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from pathlib import Path

from . import isolation, secure_files
from .broker import COMMANDS, MAX_MESSAGE, Broker, call, capability_file, loads
from .policy_store import PolicyStore, StateError
from .policy_store import shape as _shape


def doctor(socket: Path | None, capfile: Path | None) -> dict:
    """Inspect configuration descriptors only; no token reads, connections or setup."""
    checks = []
    for name, path, predicate in (
        ("broker_socket", socket, stat.S_ISSOCK),
        ("capability_file", capfile, stat.S_ISREG),
    ):
        status = "missing_configuration"
        if path is not None:
            path = Path(path).absolute()
            try:
                if any(part.is_symlink() for part in (path, *path.parents)):
                    status = "unsafe_symlink"
                else:
                    info = path.lstat()
                    status = (
                        "wrong_file_type"
                        if not predicate(info.st_mode)
                        else "unsafe_permissions"
                        if info.st_mode & 0o077
                        else "wrong_owner"
                        if info.st_uid != os.getuid()
                        else "present"
                    )
            except FileNotFoundError:
                status = "missing_path"
            except OSError:
                status = "inaccessible"
        checks.append({"check": name, "status": status})
    return {
        "schema": 1,
        "checks": checks,
        "local_prerequisites_present": all(row["status"] == "present" for row in checks),
        "deployment_verified": False,
        "limits": "Local descriptors only; no token contents, socket connection, capability "
        "authorization, whole-tool isolation, credentials or account verified. "
        "Never starts services, provisions capabilities or changes access rights.",
        "next_action": "Trusted launcher supplies paired scoped configuration and isolated "
        "tool process; use authenticated status afterward. No legacy fallback.",
    }


def client(socket: Path, capfile: Path, action: str, arguments: dict) -> dict:
    token = capability_file(capfile)
    response = call(socket, token, action, arguments)
    for alert in response.get("alerts", []):
        try:
            print(alert["text"], file=sys.stderr, flush=True)
            # Ack only AFTER output. Lost ack allows identified at-least-once replay.
            ack = call(socket, token, "ack-alert", {"episode": alert["episode"]})
            if not ack.get("ok"):
                raise StateError("Alert acknowledgement deferred.")
        except (OSError, UnicodeError, StateError):
            # Never hide a confirmed publish/result because unrelated alert delivery failed.
            response.setdefault("delivery_warnings", []).append(
                {"episode": alert["episode"], "status": "pending_replay"}
            )
    return response


def mcp(socket: Path, capfile: Path, *, input_stream=None, output_stream=None) -> None:
    """JSON-line stdio MCP; only closed broker operations. No credentials/admin API exposed."""
    input_stream, output_stream = input_stream or sys.stdin, output_stream or sys.stdout
    while raw := input_stream.readline(MAX_MESSAGE + 1):
        if len(raw.encode()) > MAX_MESSAGE:
            raise StateError("MCP request too large.")
        try:
            request = loads(raw)
        except (ValueError, StateError):
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Invalid JSON data."},
                    }
                ),
                file=output_stream,
                flush=True,
            )
            continue
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32600, "message": "Invalid request."},
                    }
                ),
                file=output_stream,
                flush=True,
            )
            continue
        if "id" not in request:
            continue
        reply = {"jsonrpc": "2.0", "id": request["id"]}
        try:
            method, params = request.get("method"), request.get("params", {})
            if method == "initialize":
                version = params.get("protocolVersion", "2024-11-05")
                if version not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
                    version = "2024-11-05"
                result = {
                    "protocolVersion": version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mgwiki-policy-broker", "version": "1"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                schema = {
                    "type": "object",
                    "required": ["action", "arguments"],
                    "additionalProperties": False,
                    "properties": {
                        "action": {"type": "string", "enum": list(COMMANDS)},
                        "arguments": {"type": "object"},
                    },
                }
                result = {
                    "tools": [
                        {
                            "name": "mgwiki",
                            "inputSchema": schema,
                            "description": "Scoped mgwiki; no shell/raw HTTP/admin API.",
                        }
                    ]
                }
            elif method == "tools/call":
                _shape(params, {"name", "arguments"})
                if params["name"] != "mgwiki":
                    raise StateError("Unknown tool.")
                arguments = params["arguments"]
                _shape(arguments, {"action", "arguments"})
                response = client(socket, capfile, arguments["action"], arguments["arguments"])
                result = {
                    "content": [{"type": "text", "text": json.dumps(response, ensure_ascii=True)}],
                    "isError": not response.get("ok", False),
                }
            else:
                raise StateError("Unknown MCP method.")
            reply["result"] = result
        except Exception:
            reply["error"] = {"code": -32602, "message": "Invalid/unavailable scoped operation."}
        print(json.dumps(reply, ensure_ascii=True), file=output_stream, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    diagnose = commands.add_parser("doctor", help="Offline broker prerequisite checks; no setup")
    diagnose.add_argument("--socket", type=Path)
    diagnose.add_argument("--capability-file", type=Path)
    activation = commands.add_parser(
        "activate",
        help="Trusted host: authenticate EXISTING grant and launch isolated tools",
    )
    activation.add_argument("--config", type=Path, required=True)
    activation.add_argument("--check-only", action="store_true", help="Authenticate; do not launch")
    create = commands.add_parser("create", help="Trusted host: create NEW private store/workspace")
    create.add_argument("--workspace", type=Path, required=True)
    create.add_argument("--state", type=Path, required=True)
    provision = commands.add_parser("provision", help="Trusted host only; not exposed to RPC")
    for item in (provision,):
        item.add_argument("--workspace", type=Path, required=True)
        item.add_argument("--state", type=Path, required=True)
    provision.add_argument("--run", required=True)
    provision.add_argument("--manifest", type=Path, required=True)
    provision.add_argument("--capability-output", type=Path, required=True)
    provision.add_argument("--expires-in", type=int, default=86400)
    renew = commands.add_parser("renew", help="Trusted host: renew scope, never promote intent")
    renew.add_argument("--workspace", type=Path, required=True)
    renew.add_argument("--state", type=Path, required=True)
    renew.add_argument("--run", required=True)
    renew.add_argument("--capability-output", type=Path, required=True)
    renew.add_argument("--expires-in", type=int, default=86400)
    serve = commands.add_parser("serve", help="Explicit host deployment; no automatic launch")
    serve.add_argument("--config", type=Path, required=True)
    for name in ("request", "mcp"):
        item = commands.add_parser(name)
        item.add_argument("--socket", type=Path, required=True)
        item.add_argument("--capability-file", type=Path, required=True)
        if name == "request":
            item.add_argument("--action", choices=COMMANDS, required=True)
            item.add_argument("--arguments", type=Path, required=True, help="JSON data only")
    inspect = commands.add_parser("inspect", help="Read-only legacy job inspection; no migration")
    inspect.add_argument("--job", type=Path, required=True)
    check = commands.add_parser("sandbox-check", help="Local namespace probe; no deployment")
    check.add_argument("--work", type=Path, required=True)
    check.add_argument("--code", type=Path, required=True)
    launch = commands.add_parser("sandbox-run", help="Explicit isolated whole-tool-process launch")
    launch.add_argument("--work", type=Path, required=True)
    launch.add_argument("--code", type=Path, required=True)
    launch.add_argument("--socket", type=Path, required=True)
    launch.add_argument("--capability-file", type=Path, required=True)
    launch.add_argument("--private-root", type=Path, action="append", required=True)
    launch.add_argument("executable", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.command == "activate":
            from .activation import activate

            result = activate(args.config, check_only=args.check_only)
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return int(result.get("returncode", 0) != 0)
        if args.command == "doctor":
            explicit = args.socket is not None or args.capability_file is not None
            socket = args.socket if explicit else os.getenv("MGWIKI_BROKER_SOCKET")
            capfile = args.capability_file if explicit else os.getenv("MGWIKI_CAPABILITY_FILE")
            result = doctor(Path(socket) if socket else None, Path(capfile) if capfile else None)
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return int(not result["local_prerequisites_present"])
        if args.command == "create":
            root = args.workspace.absolute()
            if root.exists():
                raise StateError("Fresh private workspace required; existing work never adopted.")
            root.mkdir(parents=True, mode=0o700)
            PolicyStore(args.state).create()
            result = {"status": "created", "workspace": str(root)}
        elif args.command == "provision":
            from .gateway import Gateway

            manifest = loads(args.manifest.read_bytes())
            gateway = Gateway(args.workspace, PolicyStore(args.state))
            token = gateway.provision(args.run, manifest, expires_at=time.time() + args.expires_in)
            # New protected file only. Token never printed, logged, or copied into project.
            secure_files.write(
                args.capability_output.parent, args.capability_output.name, (token + "\n").encode()
            )
            result = {"status": "provisioned", "run": args.run}
        elif args.command == "renew":
            from .gateway import Gateway

            token = Gateway(args.workspace, PolicyStore(args.state)).renew(
                args.run, expires_at=time.time() + args.expires_in
            )
            secure_files.write(
                args.capability_output.parent, args.capability_output.name, (token + "\n").encode()
            )
            result = {"status": "renewed_same_scope", "run": args.run}
        elif args.command == "serve":
            from .gateway import Gateway

            config = loads(args.config.read_bytes())
            _shape(
                config,
                {"workspace", "state", "socket", "allowed_uid"},
                {"dictionary_url", "vocabulary_database"},
            )
            os.chdir(config["workspace"])
            gateway = Gateway(
                Path.cwd(),
                PolicyStore(Path(config["state"])),
                vocabulary_database=Path(config["vocabulary_database"])
                if "vocabulary_database" in config
                else None,
                **(
                    {"dictionary_url": config["dictionary_url"]}
                    if "dictionary_url" in config
                    else {}
                ),
            )
            gateway.store.verify()
            with Broker(
                Path(config["socket"]), gateway, allowed_uid=config["allowed_uid"]
            ) as server:
                server.serve_forever()
            return 0
        elif args.command == "mcp":
            mcp(args.socket, args.capability_file)
            return 0
        elif args.command == "request":
            result = client(
                args.socket, args.capability_file, args.action, loads(args.arguments.read_bytes())
            )
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("ok") else 1
        elif args.command == "sandbox-check":
            result = isolation.check(args.work, args.code)
        elif args.command == "sandbox-run":
            executable = args.executable[1:] if args.executable[:1] == ["--"] else args.executable
            return isolation.run(
                executable,
                work=args.work,
                readonly_code=args.code,
                broker_socket=args.socket,
                capability=args.capability_file,
                private_roots=tuple(args.private_root),
            )
        else:
            names = ("job.json", "proposal.json", "receipt.json", "review.json")
            result = {
                "mode": "read_only_legacy_inspection",
                "adopted": False,
                "artifacts": {
                    name: secure_files.read(args.job, name).decode("utf-8")
                    for name in names
                    if (args.job / name).exists()
                },
                "next_action": "fresh trusted run; never manufacture historical review",
            }
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
