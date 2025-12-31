from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

@dataclass
class InstallationItem:
    """Single item to install"""
    
    item_id: str                    # Unique identifier
    item_type: str                  # "clone", "download", "pip", "npm", "shortcut"
    name: str                       # Display name
    
    # Type-specific fields
    dest: str                       # Destination path
    url: Optional[str] = None       # For clone/download
    command: Optional[List[str]] = None # For pip/npm
    
    # Validation
    expected_hash: Optional[str] = None    # SHA256 for downloads
    verify_path: Optional[str] = None      # Path to check after install
    
    # Progress tracking
    size_bytes: Optional[int] = 0

@dataclass  
class InstallationManifest:
    """Complete installation plan"""
    
    manifest_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    items: List[InstallationItem] = field(default_factory=list)
    
    # Summary
    total_size_gb: float = 0.0
    estimated_time_minutes: int = 0
    
    # Shortcuts to create after installation
    shortcuts: List[Dict[str, str]] = field(default_factory=list) # {name, command, icon}