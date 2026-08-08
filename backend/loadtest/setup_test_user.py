"""
Creates (or reuses) a test user in Postgres and prints a JWT for it.

Usage:
    python loadtest/setup_test_user.py
    export LOCUST_JWT=<printed token>
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 20 -r 5 -t 60s --csv=loadtest_results
"""
from app.db import SessionLocal
from app.db.models import User
from app.api.auth import create_access_token

TEST_EMAIL = "loadtest@example.com"


def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if not user:
            user = User(
                email=TEST_EMAIL,
                name="Load Test User",
                oauth_provider="google",
                oauth_id="loadtest",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created user: {TEST_EMAIL}")
        else:
            print(f"Reusing existing user: {TEST_EMAIL}")

        token = create_access_token(user.email)
        print("\nLOCUST_JWT=" + token)
    finally:
        db.close()


if __name__ == "__main__":
    main()
