#!/usr/bin/env python3
"""Launch the real MongoDB/API/frontend development stack; no in-memory fallback."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-mongo", action="store_true", help="Use a dedicated local MongoDB replica set on port 27019.")
    parser.add_argument("--allow-demo", action="store_true", help="Enable labeled source availability simulations.")
    args = parser.parse_args()
    environment = dict(os.environ)
    # Read only the project's ignored server-side .env; never print its values.
    try:
        from dotenv import dotenv_values
        environment = {**{k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}, **environment}
    except ImportError:
        pass
    environment["MONGODB_DATABASE"] = environment.get("MONGODB_DATABASE", "living_atlas")
    if args.allow_demo:
        environment["ENABLE_DEMO_SOURCE_WITHDRAWAL"] = "true"
    children = []
    def cleanup():
        for child in reversed(children):
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for child in reversed(children):
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
    def stop(*_):
        cleanup()
        raise SystemExit(0)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.local_mongo:
            if not shutil.which("mongod"):
                raise SystemExit("mongod is required for --local-mongo; otherwise configure MONGODB_URI.")
            from pymongo import MongoClient
            from pymongo.errors import PyMongoError
            database_dir = ROOT / "data" / "cache" / "local-mongo"
            database_dir.mkdir(parents=True, exist_ok=True)
            log_dir = ROOT / "artifacts" / "private"
            log_dir.mkdir(parents=True, exist_ok=True)
            direct_uri = "mongodb://127.0.0.1:27019/?directConnection=true"
            client = MongoClient(direct_uri, serverSelectionTimeoutMS=500)
            started_local = False
            try:
                client.admin.command("ping")
            except PyMongoError:
                children.append(subprocess.Popen([
                    "mongod", "--dbpath", str(database_dir), "--port", "27019",
                    "--bind_ip", "127.0.0.1", "--replSet", "living-atlas-dev",
                    "--logpath", str(log_dir / "mongodb.log"), "--logappend",
                ], start_new_session=True))
                started_local = True
                for _ in range(40):
                    try:
                        client.admin.command("ping")
                        break
                    except PyMongoError:
                        time.sleep(0.25)
                else:
                    raise SystemExit("Local MongoDB did not start; inspect artifacts/private/mongodb.log.")
            hello = client.admin.command("hello")
            if hello.get("setName") not in (None, "living-atlas-dev"):
                raise SystemExit("Port 27019 belongs to another replica set; choose an external MONGODB_URI.")
            if not hello.get("setName"):
                if not started_local:
                    raise SystemExit("Port 27019 is already in use by an unrecognized MongoDB; no changes made.")
                client.admin.command("replSetInitiate", {
                    "_id": "living-atlas-dev",
                    "members": [{"_id": 0, "host": "127.0.0.1:27019"}],
                })
            for _ in range(80):
                if client.admin.command("hello").get("isWritablePrimary"):
                    break
                time.sleep(0.25)
            else:
                raise SystemExit("Local MongoDB has not elected a primary.")
            client.close()
            environment["MONGODB_URI"] = "mongodb://127.0.0.1:27019/?replicaSet=living-atlas-dev"
        if not environment.get("MONGODB_URI"):
            raise SystemExit("Set server-side MONGODB_URI in .env or use --local-mongo.")
        children.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "living_atlas.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT, env=environment, start_new_session=True,
        ))
        children.append(subprocess.Popen(
            ["npm", "run", "dev", "--", "--strictPort"], cwd=ROOT / "frontend", env=environment, start_new_session=True,
        ))
        print("Living Atlas: http://127.0.0.1:5173  |  API: http://127.0.0.1:8000", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        failed = next(child.returncode for child in children if child.poll() is not None)
        if failed:
            print("A development service exited; stopping this launch.", file=sys.stderr)
        return failed or 0
    finally:
        cleanup()

if __name__ == "__main__":
    sys.exit(main())
