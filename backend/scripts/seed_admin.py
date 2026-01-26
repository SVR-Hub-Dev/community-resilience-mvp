#!/usr/bin/env python3
"""
Seed an admin user and generate an API key for initial access.

Usage:
    python scripts/seed_admin.py --email admin@example.com --name "Admin User"

This script creates an admin user (if not exists) and generates an API key
that can be used for initial API access before OAuth is configured.
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db_session
from auth.models import User, APIKey, UserRole
from auth.service import auth_service


def main():
    parser = argparse.ArgumentParser(description="Seed an admin user with API key")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--name", required=True, help="Admin user name")
    parser.add_argument("--key-name", default="Initial Admin Key", help="API key name")
    args = parser.parse_args()

    with get_db_session() as db:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == args.email).first()

        if existing_user:
            print(f"User already exists: {existing_user.email}")
            user = existing_user
            # Ensure they're an admin
            current_role = getattr(user, "role", None)
            if current_role != UserRole.ADMIN.value:
                setattr(user, "role", UserRole.ADMIN.value)
                db.commit()
                print(f"Updated user role to admin")
        else:
            # Create new admin user
            user = User(
                email=args.email,
                name=args.name,
                role=UserRole.ADMIN.value,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created admin user: {user.email}")

        # Generate API key
        full_key, key_hash, key_prefix = auth_service.generate_api_key()

        api_key = APIKey(
            user_id=user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=args.key_name,
            description="Initial admin API key for bootstrapping",
        )
        db.add(api_key)
        db.commit()

        print("\n" + "=" * 60)
        print("Admin user setup complete!")
        print("=" * 60)
        print(f"\nEmail: {user.email}")
        print(f"Name: {user.name}")
        print(f"Role: {user.role}")
        print(f"\nAPI Key (save this - it won't be shown again):")
        print(f"\n  {full_key}\n")
        print("=" * 60)
        print("\nUse this key in the Authorization header:")
        print(f"  Authorization: Bearer {full_key}")
        print("=" * 60)


if __name__ == "__main__":
    main()
