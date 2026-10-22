import pytest
from datetime import date, datetime, timezone, timedelta
from app.db.repository import Repository
from app.auth import hash_password, verify_password, generate_session_token, hash_token

def test_password_hashing():
    pw = "SuperSecure123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_session_token_generation():
    token = generate_session_token()
    assert len(token) > 20
    thash = hash_token(token)
    assert thash != token
    assert hash_token(token) == thash

@pytest.mark.asyncio
async def test_user_creation_and_auth_flow():
    email = f"test_user_{generate_session_token()[:8]}@example.com".lower()
    user = await Repository.create_user(name="Alice Test", email=email, password_hash=hash_password("mypassword"))
    assert user["id"] is not None
    assert user["name"] == "Alice Test"
    assert user["email"] == email

    # Fetch by email
    fetched = await Repository.get_user_by_email(email)
    assert fetched is not None
    assert str(fetched["id"]) == str(user["id"])

    # Session creation and lookup
    token = generate_session_token()
    token_h = hash_token(token)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await Repository.create_session(user_id=user["id"], token_hash=token_h, expires_at=expires)

    session_user = await Repository.get_user_by_session_token(token)
    assert session_user is not None
    assert str(session_user["id"]) == str(user["id"])
    assert session_user["email"] == email

    # Delete session
    await Repository.delete_session(token)
    assert await Repository.get_user_by_session_token(token) is None

@pytest.mark.asyncio
async def test_custom_labs_crud():
    user = await Repository.get_default_test_user()
    lab_name = f"Apollo Diagnostics {generate_session_token()[:6]}"
    created_lab = await Repository.create_user_lab(
        user_id=user["id"],
        name=lab_name,
        url="https://portal.apollo.com/reports",
        username="apollo_user",
        password="secret_password"
    )
    assert created_lab["name"] == lab_name
    assert created_lab["is_custom"] is True
    lab_key = created_lab["key"]

    # Verify retrieval
    labs = await Repository.get_user_labs(user["id"])
    assert any(l["key"] == lab_key for l in labs)

    # Verify get_lab_config resolves custom lab
    cfg = await Repository.get_lab_config(lab_key, user["id"])
    assert cfg is not None
    assert cfg["url"] == "https://portal.apollo.com/reports"

    # Delete custom lab
    deleted = await Repository.delete_user_lab(user["id"], lab_key)
    assert deleted is True

    # Verify deleted
    labs_after = await Repository.get_user_labs(user["id"])
    assert not any(l["key"] == lab_key for l in labs_after)

@pytest.mark.asyncio
async def test_user_isolated_runs():
    email1 = f"user1_{generate_session_token()[:6]}@example.com".lower()
    email2 = f"user2_{generate_session_token()[:6]}@example.com".lower()
    user1 = await Repository.create_user(name="User One", email=email1, password_hash=hash_password("pw1"))
    user2 = await Repository.create_user(name="User Two", email=email2, password_hash=hash_password("pw2"))

    # Create run for user 1
    run1 = await Repository.create_run(
        patient_name="User One Patient",
        patient_id="P1",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        labs=["labA"],
        user_id=user1["id"]
    )

    # Create run for user 2
    run2 = await Repository.create_run(
        patient_name="User Two Patient",
        patient_id="P2",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        labs=["labB"],
        user_id=user2["id"]
    )

    # List runs for user 1
    runs_user1 = await Repository.list_runs(user_id=user1["id"])
    assert any(str(r["id"]) == str(run1["id"]) for r in runs_user1)
    assert not any(str(r["id"]) == str(run2["id"]) for r in runs_user1)

    # List runs for user 2
    runs_user2 = await Repository.list_runs(user_id=user2["id"])
    assert any(str(r["id"]) == str(run2["id"]) for r in runs_user2)
    assert not any(str(r["id"]) == str(run1["id"]) for r in runs_user2)

    # User 2 cannot delete User 1's run
    del_forbidden = await Repository.delete_run(run1["id"], user_id=user2["id"])
    assert del_forbidden is False
    assert await Repository.get_run(run1["id"], user_id=user1["id"]) is not None

    # User 1 can delete User 1's run
    del_ok = await Repository.delete_run(run1["id"], user_id=user1["id"])
    assert del_ok is True
    assert await Repository.get_run(run1["id"], user_id=user1["id"]) is None
