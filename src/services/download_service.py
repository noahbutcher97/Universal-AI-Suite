import os
import time
import hashlib
import requests
import math
from typing import Optional, Callable
from src.utils.logger import log

class DownloadService:
    """
    Handles file downloads with progress tracking, retry logic, and validation.
    """

    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff base
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks

    @staticmethod
    def download_file(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        expected_hash: Optional[str] = None
    ) -> bool:
        """
        Download a file with retry logic.

        Args:
            url: Source URL
            dest_path: Destination file path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            expected_hash: SHA256 hash to verify (optional)

        Returns:
            True if successful, False otherwise
        """
        temp_path = dest_path + ".tmp"
        
        for attempt in range(DownloadService.MAX_RETRIES):
            try:
                headers = {}
                # Resume support if file exists
                if os.path.exists(temp_path):
                    current_size = os.path.getsize(temp_path)
                    headers["Range"] = f"bytes={current_size}-"
                else:
                    current_size = 0

                with requests.get(url, headers=headers, stream=True, timeout=20) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0)) + current_size
                    
                    mode = "ab" if current_size > 0 else "wb"
                    with open(temp_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=DownloadService.CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                current_size += len(chunk)
                                if progress_callback:
                                    progress_callback(current_size, total_size)

                # Validation
                if expected_hash:
                    if DownloadService.verify_hash(temp_path, expected_hash):
                        os.replace(temp_path, dest_path)
                        return True
                    else:
                        log.error(f"Hash mismatch for {url}")
                        os.remove(temp_path) # Corrupt download
                        return False
                
                os.replace(temp_path, dest_path)
                return True

            except Exception as e:
                log.warning(f"Download attempt {attempt+1} failed: {e}")
                time.sleep(DownloadService.RETRY_DELAY_BASE ** attempt)

        return False

    @staticmethod
    def verify_hash(file_path: str, expected_hash: str) -> bool:
        """Verify file SHA256 hash."""
        if not os.path.exists(file_path):
            return False
            
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for block in iter(lambda: f.read(4096), b""):
                    sha256.update(block)
            return sha256.hexdigest().lower() == expected_hash.lower()
        except Exception as e:
            log.error(f"Hash check error: {e}")
            return False

    @staticmethod
    def get_file_size(url: str) -> Optional[int]:
        """Get file size from URL headers without downloading."""
        try:
            r = requests.head(url, allow_redirects=True, timeout=5)
            return int(r.headers.get('content-length', 0))
        except:
            return None
