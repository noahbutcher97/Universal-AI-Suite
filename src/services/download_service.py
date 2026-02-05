"""
Download service with retry logic, progress tracking, and hash verification.

Per SPEC_v3 Section 11.4: Handle model downloads with retry, progress, and verification.
"""

import os
import time
import hashlib
import requests
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from src.utils.logger import log
from src.config.manager import config_manager


class DownloadError(Exception):
    """Base exception for download failures."""
    pass


class HashMismatchError(DownloadError):
    """Raised when downloaded file hash doesn't match expected."""
    pass


class DownloadTimeoutError(DownloadError):
    """Raised when download times out after all retries."""
    pass


@dataclass
class DownloadTask:
    """Represents a download task for queue processing."""
    url: str
    dest_path: str
    expected_hash: Optional[str] = None
    priority: int = 0  # Lower = higher priority


@dataclass
class DownloadResult:
    """Result of a download operation."""
    url: str
    dest_path: str
    success: bool
    error: Optional[str] = None
    bytes_downloaded: int = 0


def _verify_hash_worker(file_path: str, expected_hash: str) -> bool:
    """
    Standalone worker function for multiprocess hash verification.
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha256.update(block)

        actual_hash = sha256.hexdigest().lower()
        return actual_hash == expected_hash.lower()
    except Exception:
        return False


class DownloadService:
    """
    Handles file downloads with progress tracking, retry logic, and validation.

    Features:
    - Exponential backoff retry (3 attempts by default)
    - Multiprocess SHA256 hash verification (Bypasses GIL)
    - Resume support via Range headers
    - Progress callbacks
    - Concurrent download queue

    Per SPEC_v3 Section 11.4 and ARCHITECTURE_PRINCIPLES.
    """

    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff base (2^attempt seconds)
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    DEFAULT_TIMEOUT = 30  # seconds per request
    MAX_CONCURRENT = 3  # Max concurrent downloads

    def __init__(self):
        """Initialize download service."""
        self._executor = None

    @staticmethod
    def download_file(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        expected_hash: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """
        Download a file with retry logic and optional hash verification.

        Args:
            url: Source URL
            dest_path: Destination file path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            expected_hash: SHA256 hash to verify (optional)
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise

        Raises:
            HashMismatchError: If hash verification fails
            DownloadError: If download fails after all retries
        """
        # Ensure parent directory exists
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        temp_path = str(dest) + ".tmp"
        last_error = None

        for attempt in range(DownloadService.MAX_RETRIES):
            try:
                headers = {}
                
                # Hugging Face Auth
                if "huggingface.co" in url:
                    token = config_manager.get_secure("HF_TOKEN")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"

                # Resume support if temp file exists
                if os.path.exists(temp_path):
                    current_size = os.path.getsize(temp_path)
                    headers["Range"] = f"bytes={current_size}-"
                    log.debug(f"Resuming download from byte {current_size}")
                else:
                    current_size = 0

                with requests.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=timeout
                ) as response:
                    # Handle 429 Rate Limit specifically
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        retry_after = min(retry_after, 60) # Cap wait at 60s
                        log.warning(f"Rate limited. Waiting {retry_after}s...")
                        time.sleep(retry_after)
                        continue # Retry loop
                        
                    # Handle 401 Unauthorized
                    if response.status_code == 401:
                        log.error(f"Authentication failed for {url}. Please check your HF_TOKEN.")
                        return False

                    response.raise_for_status()

                    # Calculate total size
                    content_length = response.headers.get('content-length', 0)
                    total_size = int(content_length) + current_size

                    mode = "ab" if current_size > 0 else "wb"
                    with open(temp_path, mode) as f:
                        for chunk in response.iter_content(
                            chunk_size=DownloadService.CHUNK_SIZE
                        ):
                            if chunk:
                                f.write(chunk)
                                current_size += len(chunk)
                                if progress_callback:
                                    progress_callback(current_size, total_size)

                # Hash verification
                if expected_hash:
                    if not DownloadService.verify_hash(temp_path, expected_hash):
                        # Remove corrupt file
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
                        raise HashMismatchError(
                            f"Hash mismatch for {url}: expected {expected_hash}"
                        )

                # Move temp file to final destination
                os.replace(temp_path, dest_path)
                log.info(f"Downloaded successfully: {dest_path}")
                return True

            except HashMismatchError:
                # Don't retry hash mismatches - file is corrupt
                raise

            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                log.warning(
                    f"Download attempt {attempt + 1}/{DownloadService.MAX_RETRIES} "
                    f"timed out for {url}"
                )

            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                log.warning(
                    f"Download attempt {attempt + 1}/{DownloadService.MAX_RETRIES} "
                    f"failed for {url}: {e}"
                )

            except OSError as e:
                last_error = f"File error: {e}"
                log.error(f"File system error during download: {e}")
                break  # Don't retry file system errors

            # Exponential backoff before retry
            if attempt < DownloadService.MAX_RETRIES - 1:
                wait_time = DownloadService.RETRY_DELAY_BASE ** attempt
                log.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # All retries exhausted
        log.error(f"Download failed after {DownloadService.MAX_RETRIES} attempts: {url}")
        return False

    @staticmethod
    def verify_hash(file_path: str, expected_hash: str) -> bool:
        """
        Verify file SHA256 hash using a separate process to bypass GIL.

        Args:
            file_path: Path to file to verify
            expected_hash: Expected SHA256 hash (hex string)

        Returns:
            True if hash matches, False otherwise
        """
        if not os.path.exists(file_path):
            log.error(f"Cannot verify hash: file not found: {file_path}")
            return False

        log.debug(f"Verifying hash for {file_path} (Multiprocess)...")
        
        try:
            with ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_verify_hash_worker, file_path, expected_hash)
                return future.result(timeout=300) # 30s timeout for large files
        except Exception as e:
            log.error(f"Multiprocess hash verification failed: {e}")
            # Fallback to local check if multiprocess fails (rare)
            return _verify_hash_worker(file_path, expected_hash)

    @staticmethod
    def get_file_size(url: str, timeout: int = 10) -> Optional[int]:
        """
        Get file size from URL headers without downloading.

        Args:
            url: URL to check
            timeout: Request timeout in seconds

        Returns:
            File size in bytes, or None if unavailable

        Per ARCHITECTURE_PRINCIPLES: Explicit failure, no silent exceptions.
        """
        try:
            response = requests.head(url, allow_redirects=True, timeout=timeout)
            response.raise_for_status()

            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)

            log.debug(f"No content-length header for {url}")
            return None

        except requests.exceptions.Timeout:
            log.warning(f"Timeout getting file size for {url}")
            return None
        except requests.exceptions.RequestException as e:
            log.warning(f"Failed to get file size for {url}: {e}")
            return None

    def download_queue(
        self,
        tasks: List[DownloadTask],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        max_concurrent: int = MAX_CONCURRENT
    ) -> List[DownloadResult]:
        """
        Download multiple files concurrently.

        Args:
            tasks: List of DownloadTask objects
            progress_callback: Called with (url, bytes_downloaded, total_bytes)
            max_concurrent: Maximum concurrent downloads

        Returns:
            List of DownloadResult objects
        """
        results = []

        # Sort by priority (lower = higher priority)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {}

            for task in sorted_tasks:
                def make_callback(task_url):
                    def callback(downloaded, total):
                        if progress_callback:
                            progress_callback(task_url, downloaded, total)
                    return callback

                future = executor.submit(
                    self._download_task,
                    task,
                    make_callback(task.url)
                )
                futures[future] = task

            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(DownloadResult(
                        url=task.url,
                        dest_path=task.dest_path,
                        success=False,
                        error=str(e)
                    ))

        return results

    def _download_task(
        self,
        task: DownloadTask,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> DownloadResult:
        """Execute a single download task."""
        try:
            success = self.download_file(
                url=task.url,
                dest_path=task.dest_path,
                progress_callback=progress_callback,
                expected_hash=task.expected_hash
            )

            return DownloadResult(
                url=task.url,
                dest_path=task.dest_path,
                success=success,
                bytes_downloaded=os.path.getsize(task.dest_path) if success else 0
            )

        except HashMismatchError as e:
            return DownloadResult(
                url=task.url,
                dest_path=task.dest_path,
                success=False,
                error=str(e)
            )
        except Exception as e:
            return DownloadResult(
                url=task.url,
                dest_path=task.dest_path,
                success=False,
                error=str(e)
            )
