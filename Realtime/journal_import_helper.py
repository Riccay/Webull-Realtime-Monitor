"""
Journal Import Helper - Handles importing journal modules from parent directory
This module provides a robust way to import journal_db and journal_integration
regardless of where the script is run from.
"""

import sys
import os
import logging

logger = logging.getLogger(__name__)

def setup_journal_imports():
    """
    Set up the Python path to allow importing journal modules.
    Returns True if successful, False otherwise.
    """
    try:
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try multiple possible locations for journal modules
        possible_paths = [
            # Parent directory (main TradeReview folder)
            os.path.dirname(current_dir),
            # Two levels up (in case we're in a subdirectory)
            os.path.dirname(os.path.dirname(current_dir)),
            # Direct path to TradeReview
            os.path.abspath(os.path.join(current_dir, '..')),
            # Alternative direct path
            'C:/TradeReview',
            '/mnt/c/TradeReview'
        ]
        
        # Find the correct path
        journal_path = None
        for path in possible_paths:
            if os.path.exists(path):
                journal_db_path = os.path.join(path, 'journal_db.py')
                journal_int_path = os.path.join(path, 'journal_integration.py')
                
                if os.path.exists(journal_db_path) and os.path.exists(journal_int_path):
                    journal_path = path
                    break
        
        if journal_path:
            # Add to Python path if not already there
            if journal_path not in sys.path:
                sys.path.insert(0, journal_path)
            logger.info(f"Journal modules found at: {journal_path}")
            return True
        else:
            logger.error("Could not find journal modules in any expected location")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up journal imports: {str(e)}")
        return False

# Import backup manager (always available since it's in Realtime directory)
try:
    from journal_backup_manager import backup_journal, restore_journal, get_journal_backups, get_backup_manager
    logger.info("Journal backup manager imported successfully")
except ImportError as e:
    logger.error(f"Failed to import journal backup manager: {str(e)}")
    # Provide stub implementations
    def backup_journal(trigger_event="manual"):
        logger.warning("Journal backup skipped - backup manager not available")
        return None
    def restore_journal(backup_filepath):
        logger.warning("Journal restore skipped - backup manager not available")
        return False
    def get_journal_backups():
        logger.warning("Get backups skipped - backup manager not available")
        return []
    def get_backup_manager(config=None):
        return None

# Stub implementations as fallback if imports fail
class JournalStub:
    """Stub implementation for when journal modules can't be imported"""
    
    @staticmethod
    def init_journal_db():
        logger.warning("Journal database initialization skipped - modules not found")
        return False
    
    @staticmethod
    def auto_import_journal_entries():
        logger.warning("Journal auto-import skipped - modules not found")
        return 0
    
    @staticmethod
    def get_journal_entry(date_str):
        logger.warning("Journal entry retrieval skipped - modules not found")
        return None
    
    @staticmethod
    def save_journal_entry(**kwargs):
        logger.warning("Journal entry save skipped - modules not found")
        return False
    
    @staticmethod
    def get_journal_export_script():
        return ""

# Try to set up imports
if setup_journal_imports():
    try:
        # Import the actual modules
        from journal_db import init_journal_db, get_journal_entry, save_journal_entry
        from journal_integration import auto_import_journal_entries, get_journal_export_script
        logger.info("Journal modules imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import journal modules: {str(e)}")
        # Use stub implementations
        init_journal_db = JournalStub.init_journal_db
        auto_import_journal_entries = JournalStub.auto_import_journal_entries
        get_journal_entry = JournalStub.get_journal_entry
        save_journal_entry = JournalStub.save_journal_entry
        get_journal_export_script = JournalStub.get_journal_export_script
else:
    # Use stub implementations
    init_journal_db = JournalStub.init_journal_db
    auto_import_journal_entries = JournalStub.auto_import_journal_entries
    get_journal_entry = JournalStub.get_journal_entry
    save_journal_entry = JournalStub.save_journal_entry
    get_journal_export_script = JournalStub.get_journal_export_script