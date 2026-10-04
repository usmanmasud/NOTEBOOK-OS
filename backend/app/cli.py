"""Operational commands.

    python -m app.cli wait-for-db           # used by the container entrypoint
    python -m app.cli seed-demo [--no-history]
    python -m app.cli reset-demo [--no-history]
"""

import sys
import time

from sqlalchemy import text

from app.core.db import get_engine, session_factory
from app.core.logging import setup_logging


def wait_for_db(timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            print("database is reachable")
            return
        except Exception as exc:
            if time.time() > deadline:
                print(f"database not reachable after {timeout}s: {type(exc).__name__}", file=sys.stderr)
                sys.exit(1)
            time.sleep(2)


def main(argv: list[str]) -> None:
    setup_logging()
    if not argv:
        print(__doc__)
        sys.exit(2)
    command, flags = argv[0], set(argv[1:])
    with_history = "--no-history" not in flags
    if command == "wait-for-db":
        wait_for_db()
    elif command in ("seed-demo", "reset-demo"):
        from app.auth.service import get_or_create_demo_user
        from app.demo.seed import reset_demo_user, seed_demo

        db = session_factory()()
        try:
            if command == "seed-demo":
                print(seed_demo(db, with_history))
            else:
                print(reset_demo_user(db, get_or_create_demo_user(db), with_history))
        finally:
            db.close()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
