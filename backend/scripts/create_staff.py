"""Create (or promote) a STAFF account. Public signup can only create customers.

Run from the backend/ folder:
    python -m scripts.create_staff --name "Amit Sharma" --email amit@shopnest.com
You'll be asked for the password (it is not shown while typing).
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote a staff user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = UserRole.staff
            db.commit()
            print(f"Existing user {email} promoted to staff.")
            return

        password = getpass.getpass("Password (min 8 chars, letters + numbers): ")
        if len(password) < 8 or len(password) > 72 or not any(c.isdigit() for c in password) \
                or not any(c.isalpha() for c in password):
            sys.exit("Password must be 8-72 chars and contain letters and numbers.")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords do not match.")

        db.add(User(name=args.name, email=email, password_hash=hash_password(password), role=UserRole.staff))
        db.commit()
        print(f"Staff user {email} created.")


if __name__ == "__main__":
    main()
