"""Reset a user's password (admin task, for someone who forgot it).

Email-based "forgot password" needs an email service, which is out of scope, so support staff
reset it here - the same way many internal tools work.

Run from the backend/ folder:
    python -m scripts.reset_password --email rahul.demo@shopnest.com
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import check_password_strength


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user's password")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            sys.exit(f"No user with email {email}")
        password = getpass.getpass(f"New password for {email} ({user.role.value}): ")
        try:
            if not 8 <= len(password) <= 72:
                raise ValueError("Password must be 8-72 characters")
            check_password_strength(password)
        except ValueError as exc:
            sys.exit(str(exc))
        if password != getpass.getpass("Repeat new password: "):
            sys.exit("Passwords do not match.")
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Password updated for {email}.")


if __name__ == "__main__":
    main()
