"""
Webull Realtime P&L Monitor - GUI Module - v2.2
Created: 2025-05-06 16:00:00
Last Modified: 2025-05-28 14:30:00

This module provides the core graphical user interface for the Webull Realtime P&L Monitor.
It creates and manages the main GUI components and their interactions, including journal functionality.
"""

import os
import sys
import time
import logging
import traceback
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Import from common module
from webull_realtime_common import logger, TRADES_DIR
from webull_realtime_gui_components import WebullGUIComponents

class WebullGUI:
    """GUI manager for Webull Realtime P&L Monitor."""
    
    def __init__(self, config, log_parser, analytics, on_close_callback=None):
        """
        Initialize the GUI manager.
        
        Args:
            config: WebullConfig instance
            log_parser: WebullLogParser instance
            analytics: WebullAnalytics instance
            on_close_callback: Callback function when window closes
        """
        # Version info
        self.version = "2.1"
        self.created_date = "2025-05-06 16:00:00"
        self.modified_date = "2025-05-24 12:00:00"
        
        self.config = config
        self.log_parser = log_parser
        self.analytics = analytics
        self.on_close_callback = on_close_callback
        
        # Connect analytics to config for metric color scaling
        analytics.set_config(config)
        
        # GUI elements
        self.root = None
        self.style = None
        self.pnl_var = None
        self.status_var = None
        self.trade_count_var = None
        self.profit_loss_var = None
        self.last_scan_var = None
        self.date_time_var = None
        self.metrics_vars = {}  # Dictionary to store all metric StringVars
        self.chart_frame = None
        self.metrics_frames = []
        self.main_frame = None
        self.clock_frame = None
        self.pnl_frame = None
        self.pnl_title = None
        self.pnl_label = None
        self.stats_frame = None
        self.left_stats = None
        self.right_stats = None
        self.trade_label = None
        self.profit_loss_label = None
        self.trade_count = None
        self.profit_loss_count = None
        self.metrics_frame = None
        self.status_frame = None
        self.status_box = None
        self.status_label = None
        self.last_scan_label = None
        self.button_frame = None
        self.start_button = None
        self.stop_button = None
        self.export_button = None
        self.journal_button = None  # New journal button
        self.header_last_scan_label = None  # New label for last scan in header
        
        # GUI components manager
        self.components = WebullGUIComponents(self, config)
        
        # Clock thread
        self.clock_thread = None
        
        # State tracking
        self.running = False
        self.monitor_thread = None
        self.last_scan_time = datetime.now()
        self.trades = []
        self.trade_pairs = []
        
        # Callbacks
        self.on_start_callback = None
        self.on_stop_callback = None
        self.on_reset_callback = None
        
    def build_gui(self):
        """Build the GUI interface."""
        try:
            # Create main window
            self.root = tk.Tk()
            self.root.title("Webull Realtime P&L Monitor")
            self.root.geometry("600x650")
            self.root.minsize(600, 650)
            self.root.configure(background=self.config.background_color)
            
            # Configure ttk style for theming
            self.style = ttk.Style()
            
            # Create header bar
            header_frame = tk.Frame(self.root, background=self.config.primary_color, height=40)
            header_frame.pack(fill=tk.X, padx=0, pady=0)
            
            # App title
            title_label = tk.Label(
                header_frame, 
                text="Webull P&L Monitor",
                font=("Segoe UI", 12, "bold"),
                foreground="white",
                background=self.config.primary_color,
                padx=10,
                pady=10
            )
            title_label.pack(side=tk.LEFT)
            
            # Version info
            version_label = tk.Label(
                header_frame,
                text=f"v{self.version}",
                font=("Segoe UI", 8),
                foreground="white",
                background=self.config.primary_color
            )
            version_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Last scan time in header
            self.last_scan_var = tk.StringVar(value="Last scan: Never")
            self.header_last_scan_label = tk.Label(
                header_frame,
                textvariable=self.last_scan_var,
                font=("Segoe UI", 8),
                foreground="white",
                background=self.config.primary_color
            )
            self.header_last_scan_label.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
            
            # Journal button in header
            journal_button = tk.Button(
                header_frame,
                text="📝",
                font=("Segoe UI", 10, "bold"),
                background=self.config.primary_color,
                foreground="white",
                activebackground=self.config.primary_color,
                activeforeground="white",
                relief=tk.FLAT,
                borderwidth=0,
                command=self.show_journal_dialog
            )
            journal_button.pack(side=tk.RIGHT, padx=5)
            
            # Dark mode toggle button
            dark_mode_button = tk.Button(
                header_frame,
                text="🌙" if not self.config.dark_mode else "☀️",
                font=("Segoe UI", 10, "bold"),
                background=self.config.primary_color,
                foreground="white",
                activebackground=self.config.primary_color,
                activeforeground="white",
                relief=tk.FLAT,
                borderwidth=0,
                command=self.toggle_theme
            )
            dark_mode_button.pack(side=tk.RIGHT, padx=5)
            
            # Info button
            info_button = tk.Button(
                header_frame,
                text="ⓘ",
                font=("Segoe UI", 10, "bold"),
                background=self.config.primary_color,
                foreground="white",
                activebackground=self.config.primary_color,
                activeforeground="white",
                relief=tk.FLAT,
                borderwidth=0,
                command=self.show_info_dialog
            )
            info_button.pack(side=tk.RIGHT, padx=5)
            
            # Settings button
            settings_button = tk.Button(
                header_frame,
                text="⚙",
                font=("Segoe UI", 10, "bold"),
                background=self.config.primary_color,
                foreground="white",
                activebackground=self.config.primary_color,
                activeforeground="white",
                relief=tk.FLAT,
                borderwidth=0,
                command=self.show_settings_dialog
            )
            settings_button.pack(side=tk.RIGHT, padx=5)
            
            # Create main content area
            self.main_frame = tk.Frame(self.root, background=self.config.background_color)
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # Date and time display
            self.clock_frame = tk.Frame(self.main_frame, background=self.config.background_color)
            self.clock_frame.pack(fill=tk.X, pady=(0, 0))
            
            # Create variables
            self.date_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.pnl_var = tk.StringVar(value="$0.00")
            self.status_var = tk.StringVar(value="Stopped")
            self.trade_count_var = tk.StringVar(value="0")
            self.profit_loss_var = tk.StringVar(value="0 / 0 (0%)")
            
            # Create metrics variables dictionary
            self.metrics_vars = {}
            self.metrics_vars['profit_rate'] = tk.StringVar(value="0.0%")
            self.metrics_vars['avg_profit'] = tk.StringVar(value="$0.00")
            self.metrics_vars['avg_loss'] = tk.StringVar(value="$0.00")
            self.metrics_vars['profit_factor'] = tk.StringVar(value="0.00")
            self.metrics_vars['sharpe_ratio'] = tk.StringVar(value="0.00")
            self.metrics_vars['sortino_ratio'] = tk.StringVar(value="0.00")
            self.metrics_vars['max_drawdown'] = tk.StringVar(value="$0.00")
            self.metrics_vars['max_drawdown_pct'] = tk.StringVar(value="0.0%")
            self.metrics_vars['avg_duration'] = tk.StringVar(value="0.0m")
            self.metrics_vars['expectancy'] = tk.StringVar(value="$0.00")
            self.metrics_vars['consec_profits'] = tk.StringVar(value="0")
            self.metrics_vars['consec_losses'] = tk.StringVar(value="0")
            self.metrics_vars['max_consec_profits'] = tk.StringVar(value="0")
            self.metrics_vars['max_consec_losses'] = tk.StringVar(value="0")
            self.metrics_vars['largest_profit'] = tk.StringVar(value="$0.00")
            self.metrics_vars['largest_loss'] = tk.StringVar(value="$0.00")
            self.metrics_vars['profit_loss_ratio'] = tk.StringVar(value="0.00")
            self.metrics_vars['std_dev'] = tk.StringVar(value="$0.00")
            
            self.date_time_label = tk.Label(
                self.clock_frame,
                textvariable=self.date_time_var,
                font=("Segoe UI", 10),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            self.date_time_label.pack(side=tk.RIGHT, padx=10)
            
            # Start clock update thread
            self.clock_thread = threading.Thread(target=self.update_clock)
            self.clock_thread.daemon = True
            self.clock_thread.start()
            
            # P&L display
            self.pnl_frame = tk.Frame(
                self.main_frame,
                background=self.config.pnl_bg_color,
                padx=0,
                pady=10,
                borderwidth=0,
                relief=tk.FLAT
            )
            self.pnl_frame.pack(fill=tk.X, pady=(5, 10))
            
            # P&L label
            self.pnl_title = tk.Label(
                self.pnl_frame,
                text="TODAY'S P&L",
                font=("Segoe UI", 10, "bold"),
                background=self.config.pnl_bg_color,
                foreground="white"
            )
            self.pnl_title.pack(side=tk.TOP, pady=(5, 5))
            
            # P&L value only (no icon)
            self.pnl_label = tk.Label(
                self.pnl_frame,
                textvariable=self.pnl_var,
                font=("Segoe UI", 24, "bold"),
                background=self.config.pnl_bg_color,
                foreground="white"
            )
            self.pnl_label.pack(side=tk.TOP)
            
            # Trade statistics
            self.stats_frame = tk.Frame(self.main_frame, background=self.config.background_color)
            self.stats_frame.pack(fill=tk.X, pady=5)
            
            # Create two columns for stats
            self.left_stats = tk.Frame(self.stats_frame, background=self.config.background_color)
            self.left_stats.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
            self.right_stats = tk.Frame(self.stats_frame, background=self.config.background_color)
            self.right_stats.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            
            # Left column - Trade count
            self.trade_label = tk.Label(
                self.left_stats,
                text="TRADES",
                font=("Segoe UI", 10, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            self.trade_label.pack(pady=(0, 5))
            
            self.trade_count = tk.Label(
                self.left_stats,
                textvariable=self.trade_count_var,
                font=("Segoe UI", 14, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            self.trade_count.pack()
            
            # Right column - Profit/Loss
            self.profit_loss_label = tk.Label(
                self.right_stats,
                text="PROFIT / LOSS",
                font=("Segoe UI", 10, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            self.profit_loss_label.pack(pady=(0, 5))
            
            self.profit_loss_count = tk.Label(
                self.right_stats,
                textvariable=self.profit_loss_var,
                font=("Segoe UI", 14, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            self.profit_loss_count.pack()
            
            # Advanced metrics
            self.components.create_metrics_panel(self.main_frame, self.metrics_vars, self.metrics_frames)
            
            # Create chart frame
            self.chart_frame = tk.Frame(self.main_frame, background=self.config.background_color, height=200)
            self.chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Create the chart
            self.chart_widget = self.components.create_trade_chart(self.chart_frame)
            
            # Status and last scan
            self.status_frame = tk.Frame(self.main_frame, background=self.config.background_color)
            self.status_frame.pack(fill=tk.X, pady=5)
            
            # Status with indicator
            self.status_box = tk.Frame(self.status_frame, background=self.config.background_color)
            self.status_box.pack(side=tk.LEFT)
            
            # Status label
            self.status_label = tk.Label(
                self.status_box,
                textvariable=self.status_var,
                font=("Segoe UI", 10),
                background=self.config.background_color,
                foreground=self.config.loss_colors[3]  # Start with danger color
            )
            self.status_label.pack(side=tk.LEFT, padx=10)
            
            # Button frame
            self.button_frame = tk.Frame(self.main_frame, background=self.config.background_color)
            self.button_frame.pack(fill=tk.X, pady=10)
            
            # Create buttons
            self.start_button = self.components.create_modern_button(
                self.button_frame, "Start", self.on_start_button, width=8
            )
            self.start_button.pack(side=tk.LEFT, padx=(10, 5))
            
            self.stop_button = self.components.create_modern_button(
                self.button_frame, "Stop", self.on_stop_button, width=8
            )
            self.stop_button.pack(side=tk.LEFT, padx=5)
            self.stop_button.config(state=tk.DISABLED)
            
            # Journal button
            self.journal_button = self.components.create_modern_button(
                self.button_frame, "Journal", self.show_journal_dialog, width=8
            )
            self.journal_button.pack(side=tk.LEFT, padx=5)
            
            # Export button
            self.export_button = self.components.create_modern_button(
                self.button_frame, "Export", self.save_trade_data, width=8
            )
            self.export_button.pack(side=tk.RIGHT, padx=10)
            
            # Add menu bar
            self.add_menu_bar()
            
            # Add close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            
            # Initialize last scan time and update the display
            self.last_scan_time = datetime.now()
            self.last_scan_var.set(f"Last scan: {self.last_scan_time.strftime('%H:%M:%S')}")
            
            # Apply theme
            self.apply_theme()
            
            logger.info("GUI initialized with journal integration")
            
            return self.root
            
        except Exception as e:
            logger.error(f"Error building GUI: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to initialize GUI: {str(e)}")
            return None
    
    def update_clock(self):
        """Update the clock display."""
        try:
            while self.root and self.root.winfo_exists():
                now = datetime.now()
                self.date_time_var.set(now.strftime("%Y-%m-%d %H:%M:%S"))
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error updating clock: {str(e)}")
    
    def toggle_theme(self):
        """Toggle between light and dark mode."""
        self.config.toggle_dark_mode()
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the current theme to the GUI."""
        if not self.root or not self.root.winfo_exists():
            return
            
        # Configure ttk style
        if not self.style:
            self.style = ttk.Style()
        
        # Configure ttk styles (Python 3.12 compatible)
        if self.config.dark_mode:
            # Dark theme
            self.style.configure("TFrame", background=self.config.background_color)
            
            # For ttk.Button, use a simpler configuration to avoid unknown option errors
            self.style.configure("TButton", background=self.config.primary_color)
            self.style.map("TButton",
                        background=[('active', self.config.accent_color)])
            
            # For ttk.Label, just set background
            self.style.configure("TLabel", background=self.config.background_color)
            
            # Configure other ttk widgets
            self.style.configure("TCheckbutton", background=self.config.background_color)
            self.style.configure("TRadiobutton", background=self.config.background_color)
            self.style.configure("TLabelframe", background=self.config.background_color)
            self.style.configure("TLabelframe.Label", background=self.config.background_color)
        else:
            # Light theme
            self.style.configure("TFrame", background=self.config.background_color)
            
            # For ttk.Button, use a simpler configuration
            self.style.configure("TButton", background=self.config.primary_color)
            self.style.map("TButton",
                        background=[('active', self.config.accent_color)])
            
            # For ttk.Label, just set background
            self.style.configure("TLabel", background=self.config.background_color)
            
            # Configure other ttk widgets
            self.style.configure("TCheckbutton", background=self.config.background_color)
            self.style.configure("TRadiobutton", background=self.config.background_color)
            self.style.configure("TLabelframe", background=self.config.background_color)
            self.style.configure("TLabelframe.Label", background=self.config.background_color)
        
        # Update the root window
        self.root.configure(background=self.config.background_color)
        
        # Update main frames
        self.main_frame.configure(background=self.config.background_color)
        
        # Update PNL frame
        self.pnl_frame.config(background=self.config.pnl_bg_color)
        self.pnl_title.config(background=self.config.pnl_bg_color, foreground="white")
        self.pnl_label.config(background=self.config.pnl_bg_color, foreground="white")
        
        # Update stats frames
        self.stats_frame.config(background=self.config.background_color)
        self.left_stats.config(background=self.config.background_color)
        self.right_stats.config(background=self.config.background_color)
        self.trade_label.config(background=self.config.background_color, foreground=self.config.text_color)
        self.profit_loss_label.config(background=self.config.background_color, foreground=self.config.text_color)
        self.trade_count.config(background=self.config.background_color, foreground=self.config.text_color)
        self.profit_loss_count.config(background=self.config.background_color, foreground=self.config.text_color)
        
        # Update metrics frame (handle with care for compatibility with Python 3.12)
        for frame in self.metrics_frames:
            try:
                frame.config(background=self.config.background_color)
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Label):
                        try:
                            # Safely configure widget properties
                            widget.config(background=self.config.background_color)
                            widget.config(foreground=self.config.text_color)
                        except tk.TclError as e:
                            logger.debug(f"Could not fully configure widget: {str(e)}")
            except Exception as e:
                logger.debug(f"Could not update metrics frame: {str(e)}")
        
        # Update clock frame
        self.clock_frame.config(background=self.config.background_color)
        self.date_time_label.config(background=self.config.background_color, foreground=self.config.text_color)
        
        # Update status frame
        self.status_frame.config(background=self.config.background_color)
        self.status_box.config(background=self.config.background_color)
        self.status_label.config(background=self.config.background_color)
        
        # Update button frame
        self.button_frame.config(background=self.config.background_color)
        
        # Update buttons
        self.start_button.config(background=self.config.primary_color, foreground="white")
        self.stop_button.config(background=self.config.primary_color, foreground="white")
        self.export_button.config(background=self.config.primary_color, foreground="white")
        if hasattr(self, 'journal_button') and self.journal_button:
            self.journal_button.config(background=self.config.primary_color, foreground="white")
        
        # Update header last scan label
        if hasattr(self, 'header_last_scan_label') and self.header_last_scan_label:
            self.header_last_scan_label.config(background=self.config.primary_color, foreground="white")
        
        # Update chart with theme colors if available
        self.components.update_chart()
    
    def on_start_button(self):
        """Handle start button click."""
        if self.on_start_callback:
            self.on_start_callback()
    
    def on_stop_button(self):
        """Handle stop button click."""
        if self.on_stop_callback:
            self.on_stop_callback()
    
    def on_close(self):
        """Handle window close event."""
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.root.destroy()
    
    def set_callbacks(self, on_start=None, on_stop=None, on_close=None):
        """
        Set callback functions.
        
        Args:
            on_start: Callback for start button
            on_stop: Callback for stop button
            on_close: Callback for window close
        """
        self.on_start_callback = on_start
        self.on_stop_callback = on_stop
        self.on_close_callback = on_close
    
    def show_info_dialog(self):
        """Display information dialog."""
        self.components.show_info_dialog()
    
    def show_settings_dialog(self):
        """Display settings dialog."""
        self.components.show_settings_dialog()
    
    def show_journal_dialog(self):
        """Display journal dialog."""
        self.components.show_journal_dialog()
    
    def browse_log_folder(self):
        """Open dialog to select log folder."""
        self.components.browse_log_folder()
    
    def reset_data(self):
        """Reset all trade data and start fresh."""
        self.components.reset_data()
    
    def save_trade_data(self):
        """Save current trade data to file."""
        self.components.save_trade_data()
            
    def set_reset_callback(self, callback):
        """Set callback for data reset."""
        self.on_reset_callback = callback
        
    def update_gui(self, metrics_dict=None, trades=None, trade_pairs=None, position_warnings=None, is_running=False, last_scan_time=None):
        """
        Update the GUI with the latest information.
        
        Args:
            metrics_dict: Dictionary of trading metrics
            trades: List of raw trades
            trade_pairs: List of trade pairs
            position_warnings: List of position warnings
            is_running: Whether the monitor is running
            last_scan_time: Time of last scan
        """
        # Store trades for use in tagging and journal dialogs
        if trades:
            self.trades = trades
        if trade_pairs:
            self.trade_pairs = trade_pairs
            
        try:
            if not self.root or not self.root.winfo_exists():
                return
            
            # Update last scan time if provided
            if last_scan_time:
                self.last_scan_time = last_scan_time
                # Update both scan time displays
                self.last_scan_var.set(f"Last scan: {self.last_scan_time.strftime('%H:%M:%S')}")
            
            # If no metrics provided, nothing more to update
            if not metrics_dict:
                return
                
            # Update P&L display
            self.pnl_var.set(f"${metrics_dict['day_pnl']:.2f}")
            
            # Update basic metrics
            self.metrics_vars['profit_rate'].set(f"{metrics_dict['profit_rate']:.1f}%")
            self.metrics_vars['avg_profit'].set(f"${metrics_dict['avg_profit']:.2f}")
            self.metrics_vars['avg_loss'].set(f"${metrics_dict['avg_loss']:.2f}")
            self.metrics_vars['profit_factor'].set(f"{metrics_dict['profit_factor']:.2f}")
            
            # Update advanced metrics
            self.metrics_vars['sharpe_ratio'].set(f"{metrics_dict['sharpe_ratio']:.2f}")
            self.metrics_vars['sortino_ratio'].set(f"{metrics_dict['sortino_ratio']:.2f}")
            self.metrics_vars['max_drawdown'].set(f"${metrics_dict['max_drawdown']:.2f}")
            self.metrics_vars['max_drawdown_pct'].set(f"{metrics_dict['max_drawdown_pct']:.1f}%")
            self.metrics_vars['avg_duration'].set(f"{metrics_dict['avg_trade_duration']:.1f}m")
            self.metrics_vars['expectancy'].set(f"${metrics_dict['expectancy']:.2f}")
            self.metrics_vars['consec_profits'].set(f"{metrics_dict['consecutive_profits']}")
            self.metrics_vars['consec_losses'].set(f"{metrics_dict['consecutive_losses']}")
            self.metrics_vars['max_consec_profits'].set(f"{metrics_dict['max_consecutive_profits']}")
            self.metrics_vars['max_consec_losses'].set(f"{metrics_dict['max_consecutive_losses']}")
            self.metrics_vars['largest_profit'].set(f"${metrics_dict['largest_profit']:.2f}")
            self.metrics_vars['largest_loss'].set(f"${metrics_dict['largest_loss']:.2f}")
            self.metrics_vars['profit_loss_ratio'].set(f"{metrics_dict['profit_loss_ratio']:.2f}")
            self.metrics_vars['std_dev'].set(f"${metrics_dict['standard_deviation']:.2f}")
            
            # Update the metric color scale indicators
            self.components.update_metric_scales(metrics_dict)
            
            # Set color based on P&L - use a threshold to account for floating point errors
            # Use 0.01 as a threshold rather than exactly 0 to avoid floating point issues
            if metrics_dict['day_pnl'] > 0.01:
                # Profit - green
                # Change entire window background to light green
                self.root.configure(background=self.config.profit_colors[0])
                self.main_frame.configure(background=self.config.profit_colors[0])
                
                # Change panel background and text color
                self.pnl_frame.config(background=self.config.profit_colors[3])
                self.pnl_title.config(background=self.config.profit_colors[3], foreground="white")
                self.pnl_label.config(background=self.config.profit_colors[3], foreground="white")
                
                # Update stats frames
                self.stats_frame.config(background=self.config.profit_colors[0])
                self.left_stats.config(background=self.config.profit_colors[0])
                self.right_stats.config(background=self.config.profit_colors[0])
                self.trade_label.config(background=self.config.profit_colors[0])
                self.profit_loss_label.config(background=self.config.profit_colors[0])
                self.trade_count.config(background=self.config.profit_colors[0])
                self.profit_loss_count.config(background=self.config.profit_colors[0])
                
                # Update metrics frames (handle with care for compatibility with Python 3.12)
                for frame in self.metrics_frames:
                    try:
                        frame.config(background=self.config.profit_colors[0])
                        for widget in frame.winfo_children():
                            if isinstance(widget, tk.Label):
                                try:
                                    widget.config(background=self.config.profit_colors[0], foreground=self.config.text_color)
                                except tk.TclError:
                                    # If setting foreground fails, try just setting background
                                    widget.config(background=self.config.profit_colors[0])
                    except Exception as e:
                        logger.debug(f"Could not update all properties of metrics frame: {str(e)}")
                
                # Update clock frame
                self.clock_frame.config(background=self.config.profit_colors[0])
                self.date_time_label.config(background=self.config.profit_colors[0], foreground=self.config.text_color)
                
                # Update status frame
                self.status_frame.config(background=self.config.profit_colors[0])
                self.status_box.config(background=self.config.profit_colors[0])
                self.status_label.config(background=self.config.profit_colors[0])
                
                # Update button frame
                self.button_frame.config(background=self.config.profit_colors[0])
            
            elif metrics_dict['day_pnl'] < -0.01:
                # Loss - red
                # Change entire window background to light red
                self.root.configure(background=self.config.loss_colors[0])
                self.main_frame.configure(background=self.config.loss_colors[0])
                
                # Change panel background and text color
                self.pnl_frame.config(background=self.config.loss_colors[3])
                self.pnl_title.config(background=self.config.loss_colors[3], foreground="white")
                self.pnl_label.config(background=self.config.loss_colors[3], foreground="white")
                
                # Update stats frames
                self.stats_frame.config(background=self.config.loss_colors[0])
                self.left_stats.config(background=self.config.loss_colors[0])
                self.right_stats.config(background=self.config.loss_colors[0])
                self.trade_label.config(background=self.config.loss_colors[0])
                self.profit_loss_label.config(background=self.config.loss_colors[0])
                self.trade_count.config(background=self.config.loss_colors[0])
                self.profit_loss_count.config(background=self.config.loss_colors[0])
                
                # Update metrics frames (handle with care for compatibility with Python 3.12)
                for frame in self.metrics_frames:
                    try:
                        frame.config(background=self.config.loss_colors[0])
                        for widget in frame.winfo_children():
                            if isinstance(widget, tk.Label):
                                try:
                                    widget.config(background=self.config.loss_colors[0], foreground=self.config.text_color)
                                except tk.TclError:
                                    # If setting foreground fails, try just setting background
                                    widget.config(background=self.config.loss_colors[0])
                    except Exception as e:
                        logger.debug(f"Could not update all properties of metrics frame: {str(e)}")
                
                # Update clock frame
                self.clock_frame.config(background=self.config.loss_colors[0])
                self.date_time_label.config(background=self.config.loss_colors[0], foreground=self.config.text_color)
                
                # Update status frame
                self.status_frame.config(background=self.config.loss_colors[0])
                self.status_box.config(background=self.config.loss_colors[0])
                self.status_label.config(background=self.config.loss_colors[0])
                
                # Update button frame
                self.button_frame.config(background=self.config.loss_colors[0])
            
            else:
                # Neutral - use theme colors
                self.apply_theme()
            
            # Update trade counts
            self.trade_count_var.set(f"{metrics_dict['total_trades']}")
            
            # Update profit/loss ratio
            total_completed = metrics_dict['profit_trades'] + metrics_dict['losing_trades']
            profit_ratio = metrics_dict['profit_trades'] / max(1, total_completed) * 100
            self.profit_loss_var.set(f"{metrics_dict['profit_trades']} / {metrics_dict['losing_trades']} ({profit_ratio:.0f}%)")
            
            # Update status
            if position_warnings:
                self.status_var.set("WARNING: Position Imbalance")
                self.status_label.config(foreground="#f39c12")  # Warning color
            else:
                if is_running:
                    self.status_var.set("Monitoring")
                    self.status_label.config(foreground=self.config.profit_colors[3])  # Success color
                    self.start_button.config(state=tk.DISABLED)
                    self.stop_button.config(state=tk.NORMAL)
                else:
                    self.status_var.set("Stopped")
                    self.status_label.config(foreground=self.config.loss_colors[3])  # Danger color
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
            
            # Update chart
            self.components.update_chart(trades, trade_pairs)
                
        except Exception as e:
            logger.error(f"Error updating GUI: {str(e)}")
            logger.error(traceback.format_exc())
    
    def add_menu_bar(self):
        """Add menu bar to the main window."""
        try:
            # Create menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Settings", command=self.show_settings_dialog)
            file_menu.add_separator()
            file_menu.add_command(label="Export Data", command=self.components.save_trade_data)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.on_close)
            
            # Tools menu
            tools_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tools", menu=tools_menu)
            tools_menu.add_command(label="Reset Data", command=self.components.reset_data)
            tools_menu.add_command(label="Browse Log Folder", command=self.components.browse_log_folder)
            
            # Trading menu with journal integration
            trading_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Trading", menu=trading_menu)
            trading_menu.add_command(label="Trading Journal", command=self.show_journal_dialog)
            trading_menu.add_separator()
            trading_menu.add_command(label="Tag Trades", command=lambda: self.components.show_trade_tagging_dialog(self.trades, self.trade_pairs))
            
            # Help menu
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.components.show_info_dialog)
            
            logger.info("Menu bar added with journal integration")
            
        except Exception as e:
            logger.error(f"Error adding menu bar: {str(e)}")
            logger.error(traceback.format_exc())

# Version and metadata
VERSION = "2.1"
CREATED_DATE = "2025-05-06 16:00:00"
LAST_MODIFIED = "2025-05-24 12:00:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_gui",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - GUI Module - v2.1
# Created: 2025-05-06 16:00:00
# Last Modified: 2025-05-24 12:00:00
# webull_realtime_gui.py