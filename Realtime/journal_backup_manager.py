"""
Journal Backup Manager - Handles automatic backups and rotation of journal database
Created: 2025-05-28
Last Modified: 2025-05-28

This module provides robust backup functionality for the trading journal database
to prevent data loss from corruption or accidental deletion.
"""

import os
import shutil
import sqlite3
import logging
import traceback
from datetime import datetime
from pathlib import Path
import hashlib

# Import from common module
from webull_realtime_common import logger, OUTPUT_DIR

# Backup configuration
BACKUP_DIR = os.path.join(OUTPUT_DIR, 'backups', 'journal')
BACKUP_ROTATION_COUNT = 10  # Number of backups to keep
JOURNAL_DB_NAME = 'trading_journal.db'
JOURNAL_DB_PATH = os.path.join(OUTPUT_DIR, JOURNAL_DB_NAME)

class JournalBackupManager:
    """Manages automatic backups and restoration of the journal database."""
    
    def __init__(self):
        """Initialize the backup manager."""
        self.backup_dir = BACKUP_DIR
        self.ensure_backup_directory()
        self.last_backup_time = None
        logger.info(f"Journal backup manager initialized. Backup directory: {self.backup_dir}")
    
    def ensure_backup_directory(self):
        """Ensure the backup directory exists."""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            logger.debug(f"Backup directory ensured at: {self.backup_dir}")
        except Exception as e:
            logger.error(f"Failed to create backup directory: {str(e)}")
    
    def create_backup(self, trigger_event="manual"):
        """
        Create a backup of the journal database.
        
        Args:
            trigger_event (str): What triggered this backup (startup, save, shutdown, etc.)
            
        Returns:
            str: Path to the created backup file, or None if failed
        """
        try:
            # Check if journal database exists
            if not os.path.exists(JOURNAL_DB_PATH):
                logger.warning(f"Journal database not found at {JOURNAL_DB_PATH}, skipping backup")
                return None
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"journal_backup_{timestamp}_{trigger_event}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Verify database integrity before backup
            if not self.verify_database_integrity(JOURNAL_DB_PATH):
                logger.error("Journal database integrity check failed, backup aborted")
                return None
            
            # Create the backup
            shutil.copy2(JOURNAL_DB_PATH, backup_path)
            
            # Verify the backup was created successfully
            if os.path.exists(backup_path):
                backup_size = os.path.getsize(backup_path)
                original_size = os.path.getsize(JOURNAL_DB_PATH)
                
                if backup_size == original_size:
                    logger.info(f"Backup created successfully: {backup_filename} ({backup_size} bytes)")
                    self.last_backup_time = datetime.now()
                    
                    # Perform rotation after successful backup
                    self.rotate_backups()
                    
                    return backup_path
                else:
                    logger.error(f"Backup size mismatch: {backup_size} != {original_size}")
                    os.remove(backup_path)
                    return None
            else:
                logger.error("Backup file was not created")
                return None
                
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def verify_database_integrity(self, db_path):
        """
        Verify the integrity of a SQLite database.
        
        Args:
            db_path (str): Path to the database file
            
        Returns:
            bool: True if database is valid, False otherwise
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0] == "ok":
                logger.debug(f"Database integrity check passed: {db_path}")
                return True
            else:
                logger.error(f"Database integrity check failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking database integrity: {str(e)}")
            return False
    
    def rotate_backups(self):
        """
        Rotate backups, keeping only the most recent BACKUP_ROTATION_COUNT files.
        """
        try:
            # Get all backup files
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("journal_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Keep only the most recent backups
            if len(backup_files) > BACKUP_ROTATION_COUNT:
                files_to_remove = backup_files[BACKUP_ROTATION_COUNT:]
                
                for filepath, _ in files_to_remove:
                    try:
                        os.remove(filepath)
                        logger.info(f"Removed old backup: {os.path.basename(filepath)}")
                    except Exception as e:
                        logger.error(f"Failed to remove old backup {filepath}: {str(e)}")
            
            logger.debug(f"Backup rotation complete. {len(backup_files[:BACKUP_ROTATION_COUNT])} backups retained")
            
        except Exception as e:
            logger.error(f"Error rotating backups: {str(e)}")
    
    def get_available_backups(self):
        """
        Get a list of available backup files with their metadata.
        
        Returns:
            list: List of dictionaries containing backup information
        """
        try:
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("journal_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    
                    # Extract timestamp and trigger from filename
                    parts = filename.replace("journal_backup_", "").replace(".db", "").split("_")
                    if len(parts) >= 3:
                        date_str = parts[0]
                        time_str = parts[1]
                        trigger = "_".join(parts[2:])
                        
                        # Parse timestamp
                        try:
                            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                        except:
                            timestamp = datetime.fromtimestamp(os.path.getmtime(filepath))
                    else:
                        timestamp = datetime.fromtimestamp(os.path.getmtime(filepath))
                        trigger = "unknown"
                    
                    # Get file info
                    size = os.path.getsize(filepath)
                    
                    backups.append({
                        'filename': filename,
                        'filepath': filepath,
                        'timestamp': timestamp,
                        'trigger': trigger,
                        'size': size,
                        'size_mb': round(size / (1024 * 1024), 2)
                    })
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error getting available backups: {str(e)}")
            return []
    
    def restore_backup(self, backup_filepath):
        """
        Restore the journal database from a backup.
        
        Args:
            backup_filepath (str): Path to the backup file to restore
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Verify backup file exists
            if not os.path.exists(backup_filepath):
                logger.error(f"Backup file not found: {backup_filepath}")
                return False
            
            # Verify backup integrity
            if not self.verify_database_integrity(backup_filepath):
                logger.error("Backup file integrity check failed")
                return False
            
            # Create a safety backup of current database before restoring
            if os.path.exists(JOURNAL_DB_PATH):
                safety_backup = self.create_backup("pre_restore")
                if safety_backup:
                    logger.info(f"Created safety backup before restore: {safety_backup}")
            
            # Restore the backup
            shutil.copy2(backup_filepath, JOURNAL_DB_PATH)
            
            # Verify the restore
            if os.path.exists(JOURNAL_DB_PATH):
                if self.verify_database_integrity(JOURNAL_DB_PATH):
                    logger.info(f"Successfully restored journal database from: {os.path.basename(backup_filepath)}")
                    return True
                else:
                    logger.error("Restored database failed integrity check")
                    return False
            else:
                logger.error("Restore failed - database file not created")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_backup_status(self):
        """
        Get current backup status information.
        
        Returns:
            dict: Status information including last backup time, count, total size
        """
        try:
            backups = self.get_available_backups()
            
            total_size = sum(b['size'] for b in backups)
            
            status = {
                'backup_count': len(backups),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'last_backup_time': self.last_backup_time,
                'oldest_backup': backups[-1]['timestamp'] if backups else None,
                'newest_backup': backups[0]['timestamp'] if backups else None,
                'backup_directory': self.backup_dir
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting backup status: {str(e)}")
            return {
                'backup_count': 0,
                'total_size_mb': 0,
                'last_backup_time': None,
                'backup_directory': self.backup_dir
            }
    
    def calculate_file_hash(self, filepath):
        """
        Calculate SHA-256 hash of a file for integrity verification.
        
        Args:
            filepath (str): Path to the file
            
        Returns:
            str: Hex digest of the file hash
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {str(e)}")
            return None

# Global instance
backup_manager = None

def get_backup_manager():
    """Get or create the global backup manager instance."""
    global backup_manager
    if backup_manager is None:
        backup_manager = JournalBackupManager()
    return backup_manager

# Convenience functions
def backup_journal(trigger_event="manual"):
    """Create a backup of the journal database."""
    manager = get_backup_manager()
    return manager.create_backup(trigger_event)

def restore_journal(backup_filepath):
    """Restore the journal database from a backup."""
    manager = get_backup_manager()
    return manager.restore_backup(backup_filepath)

def get_journal_backups():
    """Get list of available journal backups."""
    manager = get_backup_manager()
    return manager.get_available_backups()