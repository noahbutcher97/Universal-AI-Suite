import unittest
from unittest.mock import MagicMock, patch
import customtkinter as ctk
import sys
import os
import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import List, Dict, Any, Type

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.system_service import SystemService
from src.services.setup_wizard_service import SetupWizardService
from src.schemas.environment import EnvironmentReport
from src.schemas.hardware import HardwareProfile, PlatformType
from src.schemas.recommendation import RankedCandidate, RecommendationResults, ModuleRecommendation

class UIMockFactory:
    """
    Provides safe mocks for backend services to allow UI instantiation 
    without side effects or hardware scanning.
    """
    
    @staticmethod
    def get_system_service_mock():
        mock = MagicMock(spec=SystemService)
        # Mock Environment Report
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="Test GPU",
            vram_gb=12.0,
            ram_gb=32.0,
            os_name="Windows",
            cpu_name="Test CPU",
            disk_free_gb=500.0,
            form_factor="desktop",
            os_version="10.0.19045",
            arch="AMD64"
        )
        mock.scan_full_environment.return_value = env
        mock.scan_environment.return_value = env
        # Return tuple as expected by OverviewFrame
        mock.get_gpu_info.return_value = ("nvidia", "Test GPU", 12.0)
        return mock

    @staticmethod
    def get_wizard_service_mock():
        mock = MagicMock(spec=SetupWizardService)
        # Create a concrete EnvironmentReport
        env = EnvironmentReport(
            gpu_vendor="nvidia", 
            gpu_name="Test GPU", 
            vram_gb=12.0, 
            ram_gb=32.0, 
            os_name="Windows", 
            cpu_name="Test CPU", 
            disk_free_gb=500.0, 
            form_factor="desktop",
            os_version="10.0",
            arch="AMD64"
        )
        mock.env_report = env
        mock.scan_environment.return_value = env
        return mock

    @staticmethod
    def apply_patches():
        """Apply global patches for common blocking services."""
        patchers = [
            patch('src.services.system_service.SystemService', side_effect=UIMockFactory.get_system_service_mock),
            # Patch static methods explicitly if needed
            patch('src.services.system_service.SystemService.get_gpu_info', return_value=("nvidia", "Test GPU", 12.0)),
            patch('src.services.setup_wizard_service.SetupWizardService', side_effect=UIMockFactory.get_wizard_service_mock),
            # Patch threading to prevent background tasks from running wild during tests
            patch('threading.Thread'), 
            # Patch main loop blocking calls if any
            patch('customtkinter.CTk.mainloop', MagicMock()) 
        ]
        for p in patchers:
            p.start()
        return patchers

class UICrawler:
    """
    Crawls widget trees to discover elements and validate them.
    """
    
    @staticmethod
    def get_all_widgets(root: ctk.CTkBaseClass) -> List[Any]:
        """Recursively get all widgets in a window/frame."""
        widgets = []
        children = root.winfo_children()
        for child in children:
            widgets.append(child)
            widgets.extend(UICrawler.get_all_widgets(child))
        return widgets

    @staticmethod
    def find_interactive_elements(root: ctk.CTkBaseClass) -> List[Dict[str, Any]]:
        """Find buttons, inputs, and other interactive elements."""
        elements = []
        widgets = UICrawler.get_all_widgets(root)
        
        for w in widgets:
            info = {
                "widget": w,
                "type": type(w).__name__,
                "id": str(w),
                "text": getattr(w, "_text", "") if hasattr(w, "_text") else "",
                "state": getattr(w, "_state", "normal") if hasattr(w, "_state") else "normal",
                "command": getattr(w, "_command", None) if hasattr(w, "_command") else None
            }
            
            if isinstance(w, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkSwitch, ctk.CTkRadioButton, ctk.CTkOptionMenu)):
                info["category"] = "interactive"
                elements.append(info)
            elif isinstance(w, (ctk.CTkEntry, ctk.CTkTextbox)):
                info["category"] = "input"
                elements.append(info)
                
        return elements

class ViewDiscoverer:
    """
    Automated discovery of UI View classes.
    """
    @staticmethod
    def get_all_view_classes(root_package: str = "src.ui") -> List[Type]:
        """Find all CTkFrame/CTkToplevel subclasses in the ui package."""
        view_classes = []
        
        # Helper to walk packages
        path = Path("src/ui")
        
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    # Convert path to module name
                    rel_path = os.path.relpath(os.path.join(root, file), ".")
                    module_name = rel_path.replace(os.sep, ".").replace(".py", "")
                    
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            # Check if it's a UI class defined in this module (not imported)
                            if (issubclass(obj, (ctk.CTkFrame, ctk.CTkToplevel)) and 
                                obj.__module__ == module_name):
                                view_classes.append(obj)
                    except Exception as e:
                        print(f"Warning: Could not inspect module {module_name}: {e}")
                        
        return view_classes

class DataGenerator:
    """
    Generates mock data for UI components based on parameter names.
    """
    @staticmethod
    def get_mock_arg(param_name: str, annotation: Any = None):
        """Return a suitable mock based on the argument name."""
        name = param_name.lower()
        
        if name == 'app':
            mock_app = MagicMock()
            mock_app.user_profile = MagicMock()
            return mock_app
        if name == 'navigate_callback' or name == 'on_next' or name.startswith('on_'):
            return lambda *args: None
        if name == 'task_name':
            return "Test Task"
        if name == 'model':
            # Local model mock
            m = MagicMock(spec=RankedCandidate)
            m.id = "test_model"
            m.display_name = "Test Model"
            m.tier = "sdxl"
            m.composite_score = 0.9
            m.hardware_fit_score = 0.8
            m.content_similarity_score = 0.9
            m.speed_fit_score = 0.7
            m.user_fit_score = 0.8
            m.approach_fit_score = 0.9
            m.reasoning = ["Excellent fit"]
            m.requirements = {"size_gb": 2.0, "vram_min_gb": 8.0}
            m.required_nodes = []
            return m
        if name == 'results':
            return RecommendationResults(local_recommendations=[], cloud_recommendations=[])
        if name == 'modalities':
            return ["image", "video"]
        if name == 'cloud_willingness':
            return "cloud_fallback"
        if name == 'recommendation':
            return ModuleRecommendation(
                module_id="test_mod",
                enabled=True,
                display_name="Test Module",
                description="Test Desc",
                config={},
                reasoning=[],
                warnings=[],
                components=[],
                estimated_size_gb=1.0,
                estimated_time_minutes=5
            )
        if name == 'reasoning_list':
            return ["Reason 1", "Reason 2"]
        if name == 'warnings':
            return ["Warning 1"]
        if name == 'use_case_id':
            return "uc_test"
        if name == 'title':
            return "Test Title"
        if name == 'description':
            return "Test Description"
        if name == 'icon':
            return "🚀"
        if name == 'modality':
            # CapabilityCard might expect a Modality object or just be robust to strings
            # If the code accessed .icon on a string, it expects an object.
            mock_modality = MagicMock()
            mock_modality.name = "Image"
            mock_modality.icon = "🎨"
            mock_modality.id = "image"
            return mock_modality
        if name == 'can_run_locally':
            return True
        if name == 'cloud_enabled' or name == 'is_cloud':
            return False
        if name == 'provider':
            return "openai"
        if name == 'api_key_name':
            return "OPENAI_API_KEY"
        if name == 'api_key_url':
            return "https://example.com"
        if name == 'hardware_profile':
            return HardwareProfile(
                platform=PlatformType.WINDOWS_NVIDIA,
                gpu_vendor="nvidia",
                gpu_name="Test GPU",
                vram_gb=12.0,
                unified_memory=False,
                compute_capability=8.9
            )
        if name == 'storage_free_gb':
            return 100.0
            
        # Default fallback
        return MagicMock()