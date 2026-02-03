#!/usr/bin/env python3
"""Load seed data into the database."""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db_session
from models.models import CommunityKnowledge
from services.embeddings import embed_text


def load_seed_data(force: bool = False):
    """
    Load seed knowledge entries from JSON file.

    Args:
        force: If True, skip the existing data check
    """
    seed_file = Path(__file__).parent.parent / "seed_data" / "knowledge.json"

    if not seed_file.exists():
        print(f"Seed file not found: {seed_file}")
        return

    with open(seed_file) as f:
        entries = json.load(f)

    print(f"Found {len(entries)} entries in seed file")

    with get_db_session() as db:
        existing_count = db.query(CommunityKnowledge).count()

        if existing_count > 0 and not force:
            print(f"Database already has {existing_count} entries.")
            print("Use --force to add seed data anyway.")
            return

        loaded = 0
        for entry in entries:
            print(f"  Loading: {entry['title'][:50]}...")

            # Generate embedding
            embedding = embed_text(entry["description"])

            knowledge = CommunityKnowledge(
                title=entry["title"],
                description=entry["description"],
                tags=entry.get("tags", []),
                location=entry.get("location"),
                hazard_type=entry.get("hazard_type"),
                source=entry.get("source"),
                embedding=embedding,
            )
            db.add(knowledge)
            loaded += 1

        db.commit()
        print(f"\nSuccessfully loaded {loaded} knowledge entries.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    load_seed_data(force=force)
