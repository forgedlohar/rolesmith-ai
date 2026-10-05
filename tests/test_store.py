import os

import pytest
from rolesmith_ai.store import (
    count_recent_applications_for_company,
    init_db,
    is_already_applied,
    record_application,
)


@pytest.fixture(autouse=True)
def memory_db(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("rolesmith_ai.store.get_db_path", lambda: str(db_file))
    init_db()
    yield
    if db_file.exists():
        os.remove(db_file)


def test_duplicate_application_prevention():
    job_url = "https://example.com/job/1"

    # Should not be applied initially
    assert not is_already_applied(job_url)

    # Record application
    record_application(
        job_title="Software Engineer",
        company="TechCorp",
        platform="linkedin",
        job_url=job_url,
        status="applied",
    )

    # Should be applied now
    assert is_already_applied(job_url)

    # Retry with failed status shouldn't block us from seeing it as applied? Wait
    # If the user tries to record it as failed later, we update it.
    record_application(
        job_title="Software Engineer",
        company="TechCorp",
        platform="linkedin",
        job_url=job_url,
        status="failed",
    )

    # A failed application is NOT considered already applied
    assert not is_already_applied(job_url)


def test_rate_limiting():
    # count_recent_applications_for_company

    company = "RateLimitCorp"
    assert count_recent_applications_for_company(company) == 0

    record_application(
        job_title="Role 1",
        company=company,
        platform="linkedin",
        job_url="url1",
        status="applied",
    )

    assert count_recent_applications_for_company(company) == 1

    # Failed application shouldn't count
    record_application(
        job_title="Role 2",
        company=company,
        platform="linkedin",
        job_url="url2",
        status="failed",
    )

    assert count_recent_applications_for_company(company) == 1

    # Different company shouldn't count
    record_application(
        job_title="Role 3",
        company="OtherCorp",
        platform="linkedin",
        job_url="url3",
        status="applied",
    )

    assert count_recent_applications_for_company(company) == 1
