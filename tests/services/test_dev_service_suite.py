import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from src.services.dev_service import DevService

class TestDevServiceSuite(unittest.TestCase):
    """
    Gold-standard Unit Tests for DevService.
    Follows TDD principles: verifies behavior against expected inputs/outputs independent of current implementation quirks.
    """

    def setUp(self):
        # Reset cache to ensure independent tests
        DevService.get_system_install_cmd.cache_clear()
        DevService.get_system_tools_config.cache_clear()

    @patch("platform.system")
    def test_get_system_install_cmd_windows(self, mock_system):
        """Verify Windows returns Winget commands for known tools."""
        mock_system.return_value = "Windows"
        
        # Test 1: Node.js (List format)
        cmd_node = DevService.get_system_install_cmd("node")
        self.assertEqual(cmd_node, ["winget", "install", "-e", "--id", "OpenJS.NodeJS", "--source", "winget"],
                         "Node.js on Windows should use Winget list format")

        # Test 2: UV (String format - PowerShell)
        cmd_uv = DevService.get_system_install_cmd("uv")
        self.assertIn("irm https://astral.sh/uv/install.ps1", cmd_uv,
                      "UV on Windows should use PowerShell script")

    @patch("platform.system")
    def test_get_system_install_cmd_macos(self, mock_system):
        """Verify macOS returns Brew commands."""
        mock_system.return_value = "Darwin"
        
        cmd = DevService.get_system_install_cmd("python")
        self.assertEqual(cmd, ["brew", "install", "python"],
                         "Python on macOS should use Brew")

    @patch("platform.system")
    def test_get_system_install_cmd_linux(self, mock_system):
        """Verify Linux returns Apt or Curl commands."""
        mock_system.return_value = "Linux"
        
        # Apt
        cmd_make = DevService.get_system_install_cmd("make")
        self.assertEqual(cmd_make, ["sudo", "apt", "install", "-y", "make"])
        
        # Curl (Rust)
        cmd_rust = DevService.get_system_install_cmd("rust")
        self.assertIsInstance(cmd_rust, str)
        self.assertTrue(cmd_rust.startswith("curl"), "Rust on Linux should use curl")

    @patch("shutil.which")
    def test_check_system_tool_detection(self, mock_which):
        """Verify tool detection logic."""
        # Case 1: Found
        mock_which.return_value = "/usr/bin/node"
        self.assertTrue(DevService.check_system_tool("node"))
        
        # Case 2: Not Found
        mock_which.return_value = None
        self.assertFalse(DevService.check_system_tool("nonexistent_tool"))

    @patch("platform.system")
    def test_unsupported_platform_handling(self, mock_system):
        """Verify behavior on unknown OS."""
        mock_system.return_value = "TempleOS" 
        cmd = DevService.get_system_install_cmd("node")
        self.assertIsNone(cmd, "Should return None for unsupported OS")

    def test_config_integrity(self):
        """Verify resources.json schema integrity for system_tools."""
        config = DevService.get_system_tools_config()
        self.assertIn("categories", config)
        self.assertIn("definitions", config)
        
        # Verify cross-reference
        for cat, tools in config["categories"].items():
            for tool_id in tools:
                self.assertIn(tool_id, config["definitions"], 
                              f"Tool '{tool_id}' in category '{cat}' missing definition")

if __name__ == "__main__":
    unittest.main()
