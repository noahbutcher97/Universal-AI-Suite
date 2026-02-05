"""
Unit tests for SYS-01: Multiprocessing Download Handler.
"""

import pytest
import os
import hashlib
from pathlib import Path
from src.services.download_service import DownloadService, _verify_hash_worker

@pytest.fixture
def temp_file(tmp_path):
    """Creates a temporary file with known content and hash."""
    file_path = tmp_path / "test_model.bin"
    content = b"AI Universal Suite Test Data" * 1024 # Approx 28KB
    file_path.write_bytes(content)
    
    expected_hash = hashlib.sha256(content).hexdigest()
    return file_path, expected_hash

def test_worker_function(temp_file):
    """Verify the standalone worker function correctly identifies hash."""
    file_path, expected_hash = temp_file
    
    # Correct hash
    assert _verify_hash_worker(str(file_path), expected_hash) is True
    
    # Incorrect hash
    assert _verify_hash_worker(str(file_path), "wrong_hash") is False

def test_multiprocess_verify_hash(temp_file):
    """Verify that the service correctly uses the process pool."""
    file_path, expected_hash = temp_file
    
    # This call triggers the ProcessPoolExecutor
    result = DownloadService.verify_hash(str(file_path), expected_hash)
    assert result is True

def test_verify_hash_missing_file():
    """Verify handling of missing files in multiprocess context."""
    result = DownloadService.verify_hash("non_existent_file.bin", "some_hash")
    assert result is False

def test_verify_hash_corruption(temp_file):
    """Regression test: verify corrupted files are rejected."""
    file_path, expected_hash = temp_file
    
    # Corrupt the file
    file_path.write_bytes(b"corrupted data")
    
    result = DownloadService.verify_hash(str(file_path), expected_hash)
    assert result is False

@pytest.mark.timeout(10)
def test_process_pool_termination(temp_file):
    """Verify that the process pool is correctly managed and doesn't leak."""
    file_path, expected_hash = temp_file
    
    # Repeated calls should not hang or exhaust resources
    for _ in range(5):
        assert DownloadService.verify_hash(str(file_path), expected_hash) is True
