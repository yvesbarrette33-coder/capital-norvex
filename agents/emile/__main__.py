"""CLI: python -m agents.emile <collection> <doc_id>

Exemples :
    python -m agents.emile capitalTargets ie7YRDszJQh8OlxDH4U3
    python -m agents.emile capitalTargets <doc_id> --no-open
"""
from __future__ import annotations

import sys
from .briefing_generator import generate_brief


def main():
    args = sys.argv[1:]
    open_after = "--no-open" not in args
    args = [a for a in args if not a.startswith("--")]

    if len(args) < 2:
        print("Usage: python -m agents.emile <collection> <doc_id>")
        print("       python -m agents.emile capitalTargets ie7YRDszJQh8OlxDH4U3")
        sys.exit(1)

    collection, doc_id = args[0], args[1]
    path = generate_brief(collection, doc_id, open_after=open_after)
    print(f"\nFait : {path}")


if __name__ == "__main__":
    main()
