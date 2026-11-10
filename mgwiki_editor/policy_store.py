"""Explicit, versioned SQLite state. No files opened until create/transaction."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = 1


class StateError(RuntimeError):
    """Missing, busy, corrupt or unsupported durable state; never reset automatically."""


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[^\W_][\w.-]{0,119}", value):
        raise StateError("Invalid stable identifier.")
    return value


def shape(value: dict, required: set[str], optional: set[str] = frozenset()) -> None:
    if (not isinstance(value, dict) or not required <= value.keys()
            or value.keys() - required - optional):
        raise StateError("Unknown/missing operation fields.")


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


class Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, kind: str, key: str) -> dict | None:
        row = self.connection.execute(
            "SELECT payload FROM records WHERE kind=? AND key=?", (kind, key),
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, dict):
            raise StateError("Invalid policy record.")
        return value

    def put(self, kind: str, key: str, value: dict, *, new: bool = False) -> None:
        payload = encode(value)
        if new:
            self.connection.execute(
                "INSERT INTO records(kind,key,payload) VALUES(?,?,?)", (kind, key, payload),
            )
        else:
            self.connection.execute(
                "INSERT INTO records(kind,key,payload) VALUES(?,?,?) "
                "ON CONFLICT(kind,key) DO UPDATE SET payload=excluded.payload",
                (kind, key, payload),
            )

    def rows(self, kind: str) -> list[tuple[str, dict]]:
        return [(row[0], json.loads(row[1])) for row in self.connection.execute(
            "SELECT key,payload FROM records WHERE kind=? ORDER BY key", (kind,),
        )]

    def event(self, at: float, kind: str, scope: str, payload: dict) -> int:
        if type(at) not in {int, float} or not math.isfinite(at) or at < 0:
            raise StateError("Invalid audit timestamp.")
        at = float(at)
        previous = self.connection.execute(
            "SELECT digest FROM events ORDER BY seq DESC LIMIT 1",
        ).fetchone()
        parent = previous[0] if previous else ""
        digest = fingerprint([at, kind, scope, payload, parent])
        cursor = self.connection.execute(
            "INSERT INTO events(at,kind,scope,payload,parent,digest) VALUES(?,?,?,?,?,?)",
            (at, kind, scope, encode(payload), parent, digest),
        )
        return cursor.lastrowid


class PolicyStore:
    """Broker-owned state; hash chain detects corruption, not privileged hostile rewrite."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).absolute()

    def _path_check(self) -> None:
        if any(part.is_symlink() for part in (self.path, *self.path.parents)):
            raise StateError("Symlink policy state path refused.")

    def create(self) -> None:
        self._path_check()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Existing files, including corrupt/empty ones, are never replaced.
        descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        connection = sqlite3.connect(self.path, timeout=0.2)
        try:
            connection.executescript("""
                PRAGMA synchronous=FULL;
                BEGIN IMMEDIATE;
                CREATE TABLE records(kind TEXT NOT NULL,key TEXT NOT NULL,payload TEXT NOT NULL,
                                     PRIMARY KEY(kind,key));
                CREATE TABLE events(seq INTEGER PRIMARY KEY,at REAL NOT NULL,kind TEXT NOT NULL,
                                    scope TEXT NOT NULL,payload TEXT NOT NULL,parent TEXT NOT NULL,
                                    digest TEXT NOT NULL);
                PRAGMA user_version=1;
                COMMIT;
            """)
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        self._path_check()
        if not self.path.is_file():
            raise StateError("Policy store missing; trusted initialization required.")
        connection = None
        try:
            connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=0.2)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA trusted_schema=OFF")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA:
                raise StateError("Unsupported policy store schema; no migration performed.")
            connection.execute("BEGIN IMMEDIATE")
            yield Transaction(connection)
            connection.commit()
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise StateError("Policy state busy/corrupt/inconsistent; work retained.") from exc
        finally:
            if connection is not None:
                connection.close()  # Uncommitted transaction rolls back on exceptions.

    def get(self, kind: str, key: str) -> dict | None:
        with self.transaction() as tx:
            return tx.get(kind, key)

    def events(self, scope: str | None = None) -> list[dict]:
        with self.transaction() as tx:
            query = "SELECT seq,at,kind,scope,payload FROM events"
            args = ()
            if scope is not None:
                query += " WHERE scope=?"
                args = (scope,)
            return [{"seq": row[0], "at": row[1], "kind": row[2], "scope": row[3],
                     "payload": json.loads(row[4])} for row in tx.connection.execute(
                         query + " ORDER BY seq", args,
                     )]

    def verify(self) -> None:
        with self.transaction() as tx:
            if tx.connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise StateError("Policy store integrity check failed.")
            parent = ""
            for at, kind, scope, raw, previous, digest in tx.connection.execute(
                "SELECT at,kind,scope,payload,parent,digest FROM events ORDER BY seq",
            ):
                expected = fingerprint([at, kind, scope, json.loads(raw), parent])
                if previous != parent or expected != digest:
                    raise StateError("Policy audit chain corrupt.")
                parent = digest
