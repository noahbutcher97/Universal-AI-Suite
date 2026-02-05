"""
Unit tests for SYS-02: Persistent Download Task Queue.
"""

import pytest
import os
from pathlib import Path
from src.services.download_service import DownloadService, DownloadTask
from src.services.database.engine import DatabaseManager
from src.services.database.models import Base, DownloadTaskRecord

# Use a temporary test database for persistence tests
PERSIST_TEST_DB = Path("data/test_persist_queue.db")

@pytest.fixture
def persist_service(monkeypatch):
    """Provides a DownloadService instance with a separate test database."""
    if PERSIST_TEST_DB.exists():
        try:
            os.remove(PERSIST_TEST_DB)
        except PermissionError:
            pass
    
    # Set env var BEFORE importing or initializing
    monkeypatch.setenv("AI_SUITE_DB_PATH", str(PERSIST_TEST_DB))
    
    # Force a new manager for this test
    manager = DatabaseManager(db_path=PERSIST_TEST_DB)
    manager.init_db()
    
    # Mock the global db_manager in both modules
    from src.services.database import engine
    from src.services import download_service
    monkeypatch.setattr(engine, "db_manager", manager)
    monkeypatch.setattr(download_service, "db_manager", manager)
    
    service = DownloadService()
    yield service
    
    # Teardown
    manager.engine.dispose()
    if PERSIST_TEST_DB.exists():
        try:
            os.remove(PERSIST_TEST_DB)
        except PermissionError:
            pass

def test_queue_persistent_task(persist_service):
    """Verify that tasks are correctly written to SQLite."""
    url = "https://example.com/model.safetensors"
    dest = "models/test.safetensors"
    
    persist_service.queue_persistent_task(url, dest, expected_hash="hash123", priority=1)
    
    pending = persist_service.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].url == url
    assert pending[0].dest_path == dest
    assert pending[0].priority == 1

def test_duplicate_task_prevention(persist_service):
    """Verify that adding the same task twice doesn't create duplicate DB records."""
    url = "https://example.com/model.safetensors"
    dest = "models/test.safetensors"
    
    persist_service.queue_persistent_task(url, dest)
    persist_service.queue_persistent_task(url, dest)
    
    pending = persist_service.get_pending_tasks()
    assert len(pending) == 1

def test_status_update_integration(persist_service, monkeypatch):
    """Verify that the download loop updates the DB status."""
    url = "https://example.com/model.bin"
    dest = "test_download.bin"
    
    persist_service.queue_persistent_task(url, dest)
    
    # Mock download_file to just return True and create a dummy file
    def mock_download(url, dest_path, **kwargs):
        Path(dest_path).write_bytes(b"dummy data")
        return True
        
    monkeypatch.setattr(DownloadService, "download_file", staticmethod(mock_download))
    
    task = DownloadTask(url=url, dest_path=dest)
    result = persist_service._download_task(task, None)
    
    assert result.success is True
    
    # Check status in DB
    from src.services.download_service import db_manager
    session = db_manager.get_session()
    record = session.query(DownloadTaskRecord).filter_by(url=url).first()
    assert record.status == "completed"
    session.close()
    
    # Cleanup dummy file
    if os.path.exists(dest):
        os.remove(dest)

def test_failure_persistence(persist_service, monkeypatch):
    """Verify that failed downloads are marked as failed in DB."""
    url = "https://example.com/broken.bin"
    dest = "broken.bin"
    
    persist_service.queue_persistent_task(url, dest)
    
    # Mock download_file to fail
    monkeypatch.setattr(DownloadService, "download_file", staticmethod(lambda *args, **kwargs: False))
    
    task = DownloadTask(url=url, dest_path=dest)
    persist_service._download_task(task, None)
    
    from src.services.download_service import db_manager
    session = db_manager.get_session()
    record = session.query(DownloadTaskRecord).filter_by(url=url).first()
    assert record.status == "failed"
    session.close()

def test_resume_on_startup(persist_service, monkeypatch):
    """Verify that tasks interrupted while 'running' are reset to 'pending' on init."""
    url = "https://example.com/interrupted.bin"
    dest = "interrupted.bin"
    
    # 1. Manually insert a 'running' task into DB
    from src.services.database.models import DownloadTaskRecord
    from src.services.download_service import db_manager
    session = db_manager.get_session()
    session.add(DownloadTaskRecord(
        url=url, 
        dest_path=dest, 
        status="running",
        priority=1
    ))
    session.commit()
    session.close()
    
    # 2. Re-initialize service (should trigger cleanup)
    new_service = DownloadService()
    
    # 3. Check if status was reset to pending
    pending = new_service.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].url == url
    
    session = db_manager.get_session()
    record = session.query(DownloadTaskRecord).filter_by(url=url).first()
    assert record.status == "pending"
    session.close()