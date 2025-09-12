"""
File management utilities for organizing scraping and analysis results.
"""

import os
from datetime import datetime
from typing import Tuple


class FileManager:
    """Manages file organization for scraping and analysis results."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.scraping_folder = os.path.join(base_path, "scraping_results")
        self.analysis_folder = os.path.join(base_path, "analysis_results")
        
    def ensure_folders_exist(self):
        """Create the folder structure if it doesn't exist."""
        folders = [self.scraping_folder, self.analysis_folder]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                print(f"📁 Created folder: {folder}")
    
    def get_scraping_filepath(self, website_name: str, timestamp: str = None) -> str:
        """Get the full path for a scraping result JSON file."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.ensure_folders_exist()
        filename = f"{website_name.lower()}_properties_{timestamp}.json"
        return os.path.join(self.scraping_folder, filename)
    
    def get_analysis_filepath(self, base_filename: str, file_type: str = "xlsx") -> str:
        """Get the full path for an analysis result file."""
        self.ensure_folders_exist()
        
        # Remove extension if present and add the correct one
        base_name = os.path.splitext(base_filename)[0]
        filename = f"{base_name}.{file_type}"
        
        return os.path.join(self.analysis_folder, filename)
    
    def get_analysis_json_filepath(self, base_filename: str) -> str:
        """Get the full path for an analysis JSON file."""
        return self.get_analysis_filepath(base_filename, "json")
    
    
    def list_scraping_files(self, website_name: str = None) -> list:
        """List all scraping result files, optionally filtered by website."""
        if not os.path.exists(self.scraping_folder):
            return []
        
        files = []
        for filename in os.listdir(self.scraping_folder):
            if filename.endswith('.json'):
                if website_name is None or filename.startswith(f"{website_name.lower()}_properties_"):
                    files.append(os.path.join(self.scraping_folder, filename))
        
        return sorted(files)
    
    def list_analysis_files(self) -> list:
        """List all analysis result files."""
        if not os.path.exists(self.analysis_folder):
            return []
        
        files = []
        for filename in os.listdir(self.analysis_folder):
            if filename.endswith(('.xlsx', '.json')):
                files.append(os.path.join(self.analysis_folder, filename))
        
        return sorted(files)
    
    def get_latest_scraping_file(self, website_name: str) -> str:
        """Get the path to the most recent scraping file for a website."""
        files = self.list_scraping_files(website_name)
        return files[-1] if files else None
    
    def clean_old_files(self, keep_recent: int = 10):
        """Clean up old files, keeping only the most recent ones."""
        # Clean scraping results (JSON files)
        if os.path.exists(self.scraping_folder):
            files = []
            for filename in os.listdir(self.scraping_folder):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.scraping_folder, filename)
                    files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time, newest first
            files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            for filepath, _ in files[keep_recent:]:
                try:
                    os.remove(filepath)
                    print(f"🗑️ Removed old scraping file: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"⚠️ Could not remove {filepath}: {e}")
        
        # Clean analysis results (Excel and JSON files)
        if os.path.exists(self.analysis_folder):
            files = []
            for filename in os.listdir(self.analysis_folder):
                if filename.endswith(('.xlsx', '.json')):
                    filepath = os.path.join(self.analysis_folder, filename)
                    files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time, newest first
            files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            for filepath, _ in files[keep_recent:]:
                try:
                    os.remove(filepath)
                    print(f"🗑️ Removed old analysis file: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"⚠️ Could not remove {filepath}: {e}")