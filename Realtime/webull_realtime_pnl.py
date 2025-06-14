"""
Webull Realtime P&L Monitor - Main Application Module - v1.7
Created: 2025-05-06 17:00:00
Last Modified: 2025-05-24 12:00:00

This is the main application module that coordinates all components of the
Webull Realtime P&L Monitor. It ties together the log parser, analytics,
configuration, GUI components, and journal functionality.
"""

import os
import sys
import time
import logging
import traceback
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# Import journal modules using the helper
from journal_import_helper import init_journal_db, auto_import_journal_entries, backup_journal

# Import component modules
from webull_realtime_common import logger
from webull_realtime_config import WebullConfig
from webull_realtime_log_parser import WebullLogParser
from webull_realtime_analytics import WebullAnalytics
from webull_realtime_gui import WebullGUI

class WebullRealtimePnL:
    """
    Main application class for Webull Realtime P&L Monitor.
    Coordinates all components and manages the monitoring process.
    """
    
    def __init__(self):
        """Initialize the Webull Realtime P&L Monitor application."""
        # Version info
        self.version = "1.7"
        self.created_date = "2025-05-06 17:00:00"
        self.modified_date = "2025-05-24 12:00:00"
        
        # Initialize components
        self.config = WebullConfig()
        
        # Save version info to config
        self.config.config['Settings']['version'] = self.version
        self.config.config['Settings']['created_date'] = self.created_date
        self.config.config['Settings']['modified_date'] = self.modified_date
        self.config.save_config()
        
        # Initialize journal system
        self.initialize_journal_system()
        
        # Initialize components with config
        self.log_parser = WebullLogParser(log_folder=self.config.log_folder)
        self.analytics = WebullAnalytics()
        
        # Set up connections between components
        self.analytics.set_log_parser(self.log_parser)
        self.analytics.set_config(self.config)
        
        # State tracking
        self.running = False
        self.monitor_thread = None
        self.trades = []
        self.trade_pairs = []
        self.last_scan_time = datetime.now()
        
        # GUI reference
        self.gui = None
        
    def initialize_journal_system(self):
        """Initialize the journal database and auto-import entries."""
        try:
            logger.info("Initializing journal system...")
            
            # Check if journal functions are available (not stubs)
            if hasattr(init_journal_db, '__self__') and init_journal_db.__self__.__class__.__name__ == 'JournalStub':
                logger.warning("Journal system not available - using stub implementation")
                return
            
            # Initialize the journal database
            if init_journal_db():
                logger.info("Journal database initialized successfully")
                
                # Create a startup backup
                backup_path = backup_journal("startup")
                if backup_path:
                    logger.info(f"Created startup backup: {backup_path}")
            else:
                logger.warning("Failed to initialize journal database")
            
            # Auto-import any pending journal entries
            imported_count = auto_import_journal_entries()
            if imported_count > 0:
                logger.info(f"Auto-imported {imported_count} journal entry files")
                
        except Exception as e:
            logger.error(f"Error initializing journal system: {str(e)}")
            logger.error(traceback.format_exc())
        
    def initialize_gui(self):
        """Initialize and configure the GUI."""
        # Create GUI with references to other components
        self.gui = WebullGUI(self.config, self.log_parser, self.analytics)
        
        # Set callbacks
        self.gui.set_callbacks(
            on_start=self.start_monitoring,
            on_stop=self.stop_monitoring,
            on_close=self.on_close
        )
        self.gui.set_reset_callback(self.reset_data)
        
        # Build the GUI
        root = self.gui.build_gui()
        
        return root
    
    def monitor_logs(self):
        """Monitor log files continuously and update P&L."""
        try:
            logger.info("Starting log monitoring")
            
            # Try to load historical trades
            self.analytics.load_historical_trades()
            
            # Ensure no exit condition is set
            self.running = True
            logger.info(f"Monitor thread starting with scan interval: {self.config.scan_interval} seconds")
            
            scan_count = 0
            
            while self.running:
                try:
                    # Update timestamp for "Last scan"
                    self.last_scan_time = datetime.now()
                    
                    # Log scan count periodically for debugging
                    scan_count += 1
                    if scan_count % 10 == 0:
                        logger.info(f"Completed {scan_count} scans. Last scan: {self.last_scan_time.strftime('%H:%M:%S')}")
                    
                    # Get today's log files
                    log_files = self.log_parser.find_today_log_files()
                    
                    # Always update GUI even if no log files to ensure last scan time is updated
                    # This helps visibility of the monitoring process
                    self.gui.update_gui(
                        metrics_dict=self.analytics.get_metrics_dict(),
                        trades=self.trades,
                        trade_pairs=self.trade_pairs,
                        position_warnings=self.log_parser.position_warnings,
                        is_running=self.running,
                        last_scan_time=self.last_scan_time
                    )
                    
                    if log_files:
                        # Extract trades
                        new_trades = self.log_parser.extract_trades_from_logs(log_files)
                        
                        if new_trades:
                            # Add to trades list
                            self.trades.extend(new_trades)
                            
                            # Calculate P&L
                            day_pnl = self.analytics.calculate_pnl(self.trades)
                            
                            # Match trade pairs using FIFO
                            original_trade_pairs = self.log_parser.match_buy_sell_trades(self.trades)
                            
                            # Use the appropriate averaging method based on configuration
                            if self.config.use_average_pricing:
                                logger.info(f"Using time-based average pricing with {self.config.timeframe_minutes} minute timeframe")
                                if self.config.timeframe_minutes <= 1:
                                    # If timeframe is 1 minute, use minute-based pricing
                                    logger.info("Using minute-based pricing")
                                    self.trade_pairs = self.analytics.apply_minute_based_pricing(original_trade_pairs)
                                else:
                                    # Otherwise use the configured time frame
                                    logger.info(f"Using {self.config.timeframe_minutes}-minute timeframe pricing")
                                    self.trade_pairs = self.analytics.apply_timeframe_based_pricing(
                                        original_trade_pairs, 
                                        self.config.timeframe_minutes
                                    )
                            else:
                                # Use original FIFO trade pairs
                                logger.info("Using standard FIFO trade matching without average pricing")
                                self.trade_pairs = original_trade_pairs
                            
                            # Calculate advanced metrics from trade pairs
                            metrics = self.analytics.calculate_advanced_metrics(self.trade_pairs)
                            
                            # Save trade history periodically
                            self.analytics.save_historical_trades(self.trades)
                            
                            # Check for position imbalances
                            position_warnings = self.log_parser.position_warnings
                            
                            # Update GUI
                            if self.gui:
                                self.gui.update_gui(
                                    metrics_dict=metrics,
                                    trades=self.trades,
                                    trade_pairs=self.trade_pairs,
                                    position_warnings=position_warnings,
                                    is_running=self.running,
                                    last_scan_time=self.last_scan_time
                                )
                    
                    # Get scan interval from config each time to allow it to be changed without restart
                    scan_interval = self.config.scan_interval
                    logger.debug(f"Sleeping for {scan_interval} seconds before next scan")
                    
                    # Use a more robust sleep method that checks running status frequently
                    # This allows for cleaner shutdown and more responsive controls
                    for _ in range(scan_interval * 2):  # Check twice per second
                        if self.running:
                            time.sleep(0.5)  # Sleep for half a second
                        else:
                            logger.info("Monitoring stopped during sleep")
                            break
                            
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                    logger.error(traceback.format_exc())
                    time.sleep(5)  # Longer delay on error
                    
            logger.info("Monitoring stopped")
            
        except Exception as e:
            logger.error(f"Fatal error in monitor_logs: {str(e)}")
            logger.error(traceback.format_exc())
            if self.gui and self.gui.root and self.gui.root.winfo_exists():
                tk.messagebox.showerror("Error", f"Fatal error: {str(e)}")
    
    def start_monitoring(self):
        """Start monitoring in a separate thread."""
        try:
            if not self.running:
                self.running = True
                self.monitor_thread = threading.Thread(target=self.monitor_logs)
                self.monitor_thread.daemon = True  # Thread will exit when main thread exits
                self.monitor_thread.start()
                
                logger.info("Monitoring started")
                
                # Update GUI status if GUI exists
                if self.gui:
                    self.gui.update_gui(
                        metrics_dict=self.analytics.get_metrics_dict(),
                        trades=self.trades,
                        trade_pairs=self.trade_pairs,
                        position_warnings=self.log_parser.position_warnings,
                        is_running=self.running,
                        last_scan_time=self.last_scan_time
                    )
                
        except Exception as e:
            logger.error(f"Error starting monitoring: {str(e)}")
            if self.gui and self.gui.root and self.gui.root.winfo_exists():
                tk.messagebox.showerror("Error", f"Failed to start monitoring: {str(e)}")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        try:
            if self.running:
                self.running = False
                
                # Wait for thread to terminate (with timeout)
                if self.monitor_thread and self.monitor_thread.is_alive():
                    self.monitor_thread.join(timeout=2.0)
                
                logger.info("Monitoring stopped")
                
                # Update GUI status if GUI exists
                if self.gui:
                    self.gui.update_gui(
                        metrics_dict=self.analytics.get_metrics_dict(),
                        trades=self.trades,
                        trade_pairs=self.trade_pairs,
                        position_warnings=self.log_parser.position_warnings,
                        is_running=self.running,
                        last_scan_time=self.last_scan_time
                    )
                
        except Exception as e:
            logger.error(f"Error stopping monitoring: {str(e)}")
    
    def reset_data(self):
        """Reset all trade data and start fresh."""
        try:
            # Stop monitoring
            was_running = self.running
            self.stop_monitoring()
            
            # Reset data
            self.trades = []
            self.trade_pairs = []
            
            # Reset log parser
            self.log_parser.reset()
            
            # Reset analytics
            self.analytics.reset_metrics()
            
            # Update GUI
            if self.gui:
                self.gui.update_gui(
                    metrics_dict=self.analytics.get_metrics_dict(),
                    trades=self.trades,
                    trade_pairs=self.trade_pairs,
                    position_warnings=self.log_parser.position_warnings,
                    is_running=self.running,
                    last_scan_time=self.last_scan_time
                )
            
            # Restart monitoring if it was running
            if was_running:
                time.sleep(1)  # Brief pause
                self.start_monitoring()
            
            logger.info("Trade data reset")
            
        except Exception as e:
            logger.error(f"Error resetting data: {str(e)}")
            if self.gui and self.gui.root and self.gui.root.winfo_exists():
                tk.messagebox.showerror("Error", f"Failed to reset data: {str(e)}")
    
    def on_close(self):
        """Handle application closing."""
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Set running flags to False for all threads
            self.running = False
            
            # Save trade history
            self.analytics.save_historical_trades(self.trades)
            
            # Save configuration
            self.config.save_config()
            
            # Create a shutdown backup of the journal
            try:
                backup_path = backup_journal("shutdown")
                if backup_path:
                    logger.info(f"Created shutdown backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create shutdown backup: {str(e)}")
            
            # Destroy GUI if exists
            if self.gui and self.gui.root and self.gui.root.winfo_exists():
                self.gui.root.destroy()
                
            logger.info("Application closed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
    
    def run(self):
        """Run the application."""
        try:
            # Initialize GUI
            root = self.initialize_gui()
            
            if not root:
                logger.error("Failed to initialize GUI")
                return 1
            
            # Auto-start monitoring if configured
            if self.config.auto_start:
                self.start_monitoring()
            
            # Start main loop
            root.mainloop()
            
            return 0
            
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            logger.error(traceback.format_exc())
            if self.gui and self.gui.root and self.gui.root.winfo_exists():
                tk.messagebox.showerror("Fatal Error", f"Application crashed: {str(e)}")
            return 1

def main():
    """Main entry point for the application."""
    try:
        # Create and run the monitor
        monitor = WebullRealtimePnL()
        return monitor.run()
    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Webull Realtime P&L Monitor - Main Application Module - v1.7
# Created: 2025-05-06 17:00:00
# Last Modified: 2025-05-24 12:00:00
# webull_realtime_pnl.py