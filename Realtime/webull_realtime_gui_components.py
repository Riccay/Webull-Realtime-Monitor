"""
Webull Realtime P&L Monitor - GUI Components Module - v2.8
Created: 2025-05-07 10:45:00
Last Modified: 2025-05-24 12:00:00

This module provides specialized GUI components for the Webull Realtime P&L Monitor.
It handles dialogs, charts, and other complex UI elements including journal functionality.
"""

import os
import sys
import time
import logging
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from datetime import datetime, date
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import configparser

# Import from common module
from webull_realtime_common import logger, TRADES_DIR, CONFIG_FILE

# Import journal functionality - look in parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from journal_db import save_journal_entry, get_journal_entry
from journal_integration import get_journal_export_script

class ToolTip:
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        """
        Initialize the tooltip.
        
        Args:
            widget: The widget to attach the tooltip to
            text: The text to display in the tooltip
        """
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<Motion>", self.motion)
    
    def schedule(self, event=None):
        """Schedule the tooltip to appear after a delay."""
        self.id = self.widget.after(500, self.show)
    
    def motion(self, event=None):
        """Update tooltip position based on mouse movement."""
        self.x, self.y = event.x + self.widget.winfo_rootx() + 20, event.y + self.widget.winfo_rooty() + 10
        if self.tooltip_window:
            self.tooltip_window.wm_geometry(f"+{self.x}+{self.y}")
    
    def show(self):
        """Display the tooltip."""
        self.id = None
        # Create a new tooltip window
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        # Remove the window decoration
        tw.wm_overrideredirect(True)
        # Make the window appear a little below and to the right of the mouse
        tw.wm_geometry(f"+{self.x}+{self.y}")
        
        # Create the tooltip label
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffdd", relief="solid", borderwidth=1,
            wraplength=300, padx=4, pady=4, font=("Segoe UI", 8)
        )
        label.pack(fill="both")
    
    def hide(self, event=None):
        """Hide the tooltip."""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class WebullGUIComponents:
    """GUI components manager for Webull Realtime P&L Monitor."""
    
    def __init__(self, gui_manager, config):
        """
        Initialize the GUI components manager.
        
        Args:
            gui_manager: Parent WebullGUI instance
            config: WebullConfig instance
        """
        # Version info
        self.version = "2.8"
        self.created_date = "2025-05-07 10:45:00"
        self.modified_date = "2025-05-24 12:00:00"
        
        self.gui = gui_manager
        self.config = config
        
        # Chart components
        self.fig = None
        self.ax = None
        self.canvas = None
        
        # Metric scale indicators
        self.metric_scales = {}
        
        # Define tooltips for metrics
        self.metric_tooltips = {
            'profit_rate': "Percentage of trades that resulted in profit",
            'avg_profit': "Average dollar amount gained on profitable trades",
            'avg_loss': "Average dollar amount lost on unprofitable trades",
            'profit_factor': "Total profit divided by total loss (higher is better)",
            'sharpe_ratio': "Risk-adjusted return metric (higher is better)",
            'max_drawdown': "Largest drop from peak to trough in account value",
            'avg_duration': "Average time a position is held in minutes",
            'expectancy': "Average profit/loss expected from each trade",
            'consec_profits': "Current streak of profitable trades",
            'consec_losses': "Current streak of losing trades",
            'max_consec_profits': "Longest streak of consecutive profitable trades",
            'max_consec_losses': "Longest streak of consecutive losing trades",
            'largest_profit': "Biggest single winning trade",
            'largest_loss': "Biggest single losing trade",
            'profit_loss_ratio': "Ratio of average profit to average loss (higher is better)",
            'std_dev': "Standard deviation of P&L (lower volatility is generally better)"
        }
    
    def create_modern_button(self, parent, text, command, width=None):
        """
        Create a modern styled button.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button command
            width: Button width
            
        Returns:
            Button widget
        """
        button = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 9),
            command=command,
            background=self.config.primary_color,
            foreground="white",
            activebackground=self.config.primary_color,
            activeforeground="white",
            relief=tk.FLAT,
            width=width
        )
        return button
    
    def create_trade_chart(self, parent):
        """
        Create a matplotlib chart for displaying trade performance.
        
        Args:
            parent: Parent widget
            
        Returns:
            Chart widget
        """
        try:
            # Create figure with theme-aware colors
            fig_bg_color = self.config.background_color if self.config.dark_mode else 'white'
            text_color = self.config.text_color
            
            # Create figure and canvas with 25% more height
            self.fig = plt.Figure(figsize=(4, 3.75), dpi=100, facecolor=fig_bg_color)
            self.ax = self.fig.add_subplot(111)
            
            # Theme the chart
            if self.config.dark_mode:
                self.ax.set_facecolor(self.config.background_color)
                self.ax.tick_params(colors=text_color)
                self.ax.spines['bottom'].set_color(text_color)
                self.ax.spines['top'].set_color(text_color)
                self.ax.spines['left'].set_color(text_color)
                self.ax.spines['right'].set_color(text_color)
                self.ax.xaxis.label.set_color(text_color)
                self.ax.yaxis.label.set_color(text_color)
                self.ax.title.set_color(text_color)
            
            self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Draw initial empty chart
            self.update_chart()
            
            return self.canvas.get_tk_widget()
            
        except Exception as e:
            logger.error(f"Error creating chart: {str(e)}")
            logger.error(traceback.format_exc())
            return tk.Frame(parent)  # Return empty frame on error
    
    def update_chart(self, trades=None, trade_pairs=None):
        """
        Update the trade performance chart with current data.
        
        Args:
            trades: List of raw trades
            trade_pairs: List of trade pairs
        """
        try:
            if not hasattr(self, 'ax') or not hasattr(self, 'fig') or not hasattr(self, 'canvas'):
                return
                
            # Clear previous plot
            self.ax.clear()
            
            # Set theme colors
            text_color = self.config.text_color
            grid_color = self.config.text_color if self.config.dark_mode else '#dddddd'
            
            # Apply theme to chart
            self.ax.set_facecolor(self.config.background_color if self.config.dark_mode else 'white')
            self.ax.tick_params(colors=text_color, labelsize=6)  # Reduced font size by ~50%
            for spine in self.ax.spines.values():
                spine.set_color(text_color)
            
            # Check if we have any data
            if not trades and not trade_pairs:
                # No data - clean display without ticks
                self.ax.set_xticks([])  # Remove x-axis ticks
                self.ax.set_yticks([])  # Remove y-axis ticks
                self.canvas.draw()
                return
            
            # Check if we have any trade pairs
            if not trade_pairs and trades:
                # If no trade pairs, just show raw trades
                df = pd.DataFrame(trades)
                
                # Ensure proper data types
                df['Quantity'] = pd.to_numeric(df['Quantity'])
                df['Price'] = pd.to_numeric(df['Price'])
                
                # Convert Date and Time to datetime
                df['DateTime'] = pd.to_datetime(
                    df['Date'].astype(str) + ' ' + 
                    df['Time'].astype(str)
                )
                df = df.sort_values('DateTime')
                
                # Create a P&L column and calculate cumulative P&L
                df['TradeValue'] = df.apply(
                    lambda row: row['Price'] * row['Quantity'] if row['Side'].upper() == 'SELL' 
                    else -row['Price'] * row['Quantity'], 
                    axis=1
                )
                
                # Subtract commissions
                if 'Commission' in df.columns:
                    df['TradeValue'] = df['TradeValue'] - pd.to_numeric(df['Commission'])
                    
                # Calculate cumulative P&L
                df['CumulativePnL'] = df['TradeValue'].cumsum()
                
                # Plot cumulative P&L
                line_color = self.config.profit_colors[3] if df['CumulativePnL'].iloc[-1] > 0 else self.config.loss_colors[3]
                self.ax.plot(df['DateTime'], df['CumulativePnL'], marker='o', linestyle='-', 
                           color=line_color)
                
                # No title as requested
            
            else:
                # Use completed trade pairs for more advanced chart
                df = pd.DataFrame(trade_pairs)
                
                # Convert date strings to datetime
                df['SellTimeObj'] = pd.to_datetime(df['SellTime'])
                df = df.sort_values('SellTimeObj')
                
                # Calculate cumulative P&L
                df['CumulativePnL'] = df['PnL'].cumsum()
                
                # Basic P&L chart
                line_color = self.config.profit_colors[3] if df['CumulativePnL'].iloc[-1] > 0 else self.config.loss_colors[3]
                self.ax.plot(df['SellTimeObj'], df['CumulativePnL'], marker='o', linestyle='-', 
                           color=line_color)
                
                # Add trade markers - green for profit, red for loss
                profits = df[df['Result'] == 'Profit']
                losses = df[df['Result'] == 'Loss']
                
                if not profits.empty:
                    self.ax.scatter(profits['SellTimeObj'], profits['CumulativePnL'], 
                                  color=self.config.profit_colors[3], s=30, zorder=5)
                
                if not losses.empty:
                    self.ax.scatter(losses['SellTimeObj'], losses['CumulativePnL'], 
                                  color=self.config.loss_colors[3], s=30, zorder=5)
                
                # No title as requested
            
            # Add horizontal line at zero
            self.ax.axhline(y=0, color=text_color, linestyle='-', alpha=0.3)
            
            # Add grid
            self.ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)
            
            # Format chart - using smaller fonts
            self.ax.set_ylabel("P&L ($)", color=text_color, fontsize=6)  # Reduced font size by ~50%
            self.ax.set_xlabel("Time", color=text_color, fontsize=6)  # Add back the x-axis label
            
            # Format x-axis to show times better
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # Rotate x-axis labels - using smaller font
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right', fontsize=6)  # Reduced font size by ~50%
            
            # Adjust layout with more padding for the smaller text
            self.fig.tight_layout(pad=1.1)
            
            # Draw the updated chart
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating chart: {str(e)}")
            logger.error(traceback.format_exc())
    
    def create_metric_scale_indicator(self, parent, scale_value):
        """
        Create a color scale indicator showing a value from 1-10.
        
        Args:
            parent: Parent widget
            scale_value: Value on the scale (1-10)
            
        Returns:
            Frame widget containing the scale indicator
        """
        try:
            # Ensure scale value is in range 1-10
            scale_value = max(1, min(10, scale_value))
            
            # Create frame to hold the indicator
            frame = tk.Frame(parent, background=self.config.background_color)
            
            # Get the color for this scale value
            indicator_color = self.config.metric_colors[scale_value-1]
            
            # Create a single indicator block with the appropriate color
            indicator = tk.Frame(
                frame,
                width=20,  # Wider single block for better visibility
                height=4,
                background=indicator_color,
                bd=0,
                highlightthickness=0
            )
            indicator.pack(side=tk.LEFT, padx=0, pady=0)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error creating metric scale indicator: {str(e)}")
            
            # Return empty frame on error
            return tk.Frame(parent, background=self.config.background_color)
    
    def create_color_scale_legend(self, parent):
        """
        Create a legend showing the full color scale from 1-10.
        Each color on its own line.
        
        Args:
            parent: Parent widget
            
        Returns:
            Frame containing the color scale legend
        """
        try:
            # Create container frame for the legend
            legend_frame = tk.Frame(parent, background=self.config.background_color, padx=2)
            
            # Title
            title_label = tk.Label(
                legend_frame,
                text="Scale",
                font=("Segoe UI", 7, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            title_label.pack(pady=(0, 2))
            
            # Create 10 rows, one for each color level
            for i in range(10):
                # Create a row for this color level
                color_row = tk.Frame(legend_frame, background=self.config.background_color)
                color_row.pack(fill=tk.X, pady=0)
                
                # Color block with number
                block_frame = tk.Frame(color_row, background=self.config.background_color)
                block_frame.pack(side=tk.LEFT, padx=1, pady=0)
                
                # The color block
                color_block = tk.Frame(
                    block_frame,
                    width=8,
                    height=8,
                    background=self.config.metric_colors[i],
                    bd=0
                )
                color_block.pack(side=tk.LEFT)
                
                # The number beside the block
                tk.Label(
                    block_frame,
                    text=f"{i+1}",
                    font=("Segoe UI", 6),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                ).pack(side=tk.LEFT, padx=(2, 0))
            
            return legend_frame
            
        except Exception as e:
            logger.error(f"Error creating color scale legend: {str(e)}")
            
            # Return empty frame on error
            return tk.Frame(parent, background=self.config.background_color)
    
    def create_metrics_panel(self, parent, metrics_vars, metrics_frames):
        """
        Create the trading metrics panel.
        
        Args:
            parent: Parent widget
            metrics_vars: Dictionary of metrics StringVars
            metrics_frames: List to store created frames
        """
        try:
            # Advanced metrics
            metrics_frame = ttk.LabelFrame(parent, text="Trading Metrics", padding=(5, 5, 5, 5))
            metrics_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Create main container with color scale legend on the right
            main_container = tk.Frame(metrics_frame, background=self.config.background_color)
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # Create color scale legend on the right
            legend_frame = self.create_color_scale_legend(main_container)
            legend_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0), anchor=tk.NE)
            
            # Create a grid frame inside the metrics frame
            metrics_grid = tk.Frame(main_container, background=self.config.background_color)
            metrics_grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            metrics_frames.append(metrics_grid)
            
            # Clear any existing metric scales
            self.metric_scales = {}
            
            # Basic metrics (row 0)
            basic_metrics = [
                ("Profit Rate", 'profit_rate'),
                ("Avg Profit", 'avg_profit'),
                ("Avg Loss", 'avg_loss'),
                ("Profit Factor", 'profit_factor')
            ]
            
            for col, (title, var_key) in enumerate(basic_metrics):
                # Create frame for this metric
                metric_frame = tk.Frame(metrics_grid, background=self.config.background_color)
                metric_frame.grid(row=0, column=col, padx=5, pady=5)
                metrics_frames.append(metric_frame)
                
                # Title label - we'll add tooltip to this
                title_label = tk.Label(
                    metric_frame,
                    text=title,
                    font=("Segoe UI", 8, "bold"),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                )
                title_label.pack()
                
                # Add tooltip to title
                if var_key in self.metric_tooltips:
                    ToolTip(title_label, self.metric_tooltips[var_key])
                
                # Value
                tk.Label(
                    metric_frame,
                    textvariable=metrics_vars[var_key],
                    font=("Segoe UI", 10),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                ).pack()
                
                # Add scale indicator
                scale_frame = tk.Frame(metric_frame, background=self.config.background_color)
                scale_frame.pack(pady=(2, 0))
                
                # Store reference to the scale indicator
                self.metric_scales[var_key] = {
                    'frame': scale_frame,
                    'indicator': None,
                    'scale_value': 5  # Default middle value
                }
            
            # Advanced metrics - row 1
            advanced_metrics1 = [
                ("Sharpe Ratio", 'sharpe_ratio'),
                ("Max Drawdown", 'max_drawdown'),
                ("Avg Duration", 'avg_duration'),
                ("Expectancy", 'expectancy')
            ]
            
            for col, (title, var_key) in enumerate(advanced_metrics1):
                # Create frame for this metric
                metric_frame = tk.Frame(metrics_grid, background=self.config.background_color)
                metric_frame.grid(row=1, column=col, padx=5, pady=5)
                metrics_frames.append(metric_frame)
                
                # Title label - we'll add tooltip to this
                title_label = tk.Label(
                    metric_frame,
                    text=title,
                    font=("Segoe UI", 8, "bold"),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                )
                title_label.pack()
                
                # Add tooltip to title
                if var_key in self.metric_tooltips:
                    ToolTip(title_label, self.metric_tooltips[var_key])
                
                # Value
                tk.Label(
                    metric_frame,
                    textvariable=metrics_vars[var_key],
                    font=("Segoe UI", 10),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                ).pack()
                
                # Add scale indicator
                scale_frame = tk.Frame(metric_frame, background=self.config.background_color)
                scale_frame.pack(pady=(2, 0))
                
                # Store reference to the scale indicator
                self.metric_scales[var_key] = {
                    'frame': scale_frame,
                    'indicator': None,
                    'scale_value': 5  # Default middle value
                }
            
            # Advanced metrics - row 2 with renamed "Current" metrics
            advanced_metrics2 = [
                ("Current Profit Streak", 'consec_profits'),
                ("Current Loss Streak", 'consec_losses'),
                ("Max Profit Streak", 'max_consec_profits'),
                ("Max Loss Streak", 'max_consec_losses')
            ]
            
            for col, (title, var_key) in enumerate(advanced_metrics2):
                # Create frame for this metric
                metric_frame = tk.Frame(metrics_grid, background=self.config.background_color)
                metric_frame.grid(row=2, column=col, padx=5, pady=5)
                metrics_frames.append(metric_frame)
                
                # Title label - we'll add tooltip to this
                title_label = tk.Label(
                    metric_frame,
                    text=title,
                    font=("Segoe UI", 8, "bold"),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                )
                title_label.pack()
                
                # Add tooltip to title
                if var_key in self.metric_tooltips:
                    ToolTip(title_label, self.metric_tooltips[var_key])
                
                # Value
                tk.Label(
                    metric_frame,
                    textvariable=metrics_vars[var_key],
                    font=("Segoe UI", 10),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                ).pack()
                
                # Add scale indicator
                scale_frame = tk.Frame(metric_frame, background=self.config.background_color)
                scale_frame.pack(pady=(2, 0))
                
                # Store reference to the scale indicator
                self.metric_scales[var_key] = {
                    'frame': scale_frame,
                    'indicator': None,
                    'scale_value': 5  # Default middle value
                }
            
            # Advanced metrics - row 3
            advanced_metrics3 = [
                ("Largest Profit", 'largest_profit'),
                ("Largest Loss", 'largest_loss'),
                ("Profit/Loss Ratio", 'profit_loss_ratio'),
                ("Std Deviation", 'std_dev')
            ]
            
            for col, (title, var_key) in enumerate(advanced_metrics3):
                # Create frame for this metric
                metric_frame = tk.Frame(metrics_grid, background=self.config.background_color)
                metric_frame.grid(row=3, column=col, padx=5, pady=5)
                metrics_frames.append(metric_frame)
                
                # Title label - we'll add tooltip to this
                title_label = tk.Label(
                    metric_frame,
                    text=title,
                    font=("Segoe UI", 8, "bold"),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                )
                title_label.pack()
                
                # Add tooltip to title
                if var_key in self.metric_tooltips:
                    ToolTip(title_label, self.metric_tooltips[var_key])
                
                # Value
                tk.Label(
                    metric_frame,
                    textvariable=metrics_vars[var_key],
                    font=("Segoe UI", 10),
                    background=self.config.background_color,
                    foreground=self.config.text_color
                ).pack()
                
                # Add scale indicator
                scale_frame = tk.Frame(metric_frame, background=self.config.background_color)
                scale_frame.pack(pady=(2, 0))
                
                # Store reference to the scale indicator
                self.metric_scales[var_key] = {
                    'frame': scale_frame,
                    'indicator': None,
                    'scale_value': 5  # Default middle value
                }
                
        except Exception as e:
            logger.error(f"Error creating metrics panel: {str(e)}")
            logger.error(traceback.format_exc())
    
    def update_metric_scales(self, metrics_dict):
        """
        Update metric scale indicators based on current metrics.
        
        Args:
            metrics_dict: Dictionary of current metrics
        """
        try:
            # Update each metric scale
            for metric_key, scale_info in self.metric_scales.items():
                if metric_key in metrics_dict:
                    metric_value = metrics_dict[metric_key]
                    
                    # Get color and scale value for this metric
                    color, scale_value = self.config.get_metric_color_scale(metric_value, metric_key)
                    
                    # If scale value changed, update the indicator
                    if scale_value != scale_info['scale_value']:
                        # Clear the current indicator
                        if scale_info['indicator']:
                            scale_info['indicator'].destroy()
                        
                        # Create new indicator
                        scale_info['indicator'] = self.create_metric_scale_indicator(
                            scale_info['frame'], scale_value
                        )
                        scale_info['indicator'].pack(fill=tk.X)
                        
                        # Update stored scale value
                        scale_info['scale_value'] = scale_value
                        
        except Exception as e:
            logger.error(f"Error updating metric scales: {str(e)}")
            logger.error(traceback.format_exc())

    def show_info_dialog(self):
        """Display information dialog."""
        try:
            # Get metrics
            metrics = self.gui.analytics.get_metrics_dict()
            
            info_text = f"""
Version: {self.gui.version}
Created: {self.gui.created_date}
Last Modified: {self.gui.modified_date}

Log Folder:
{self.config.log_folder}

Total Trades: {metrics['total_trades']}
- Profits: {metrics['profit_trades']}
- Losses: {metrics['losing_trades']}
- Profit Rate: {metrics['profit_rate']:.1f}%
- Avg Profit: ${metrics['avg_profit']:.2f}
- Avg Loss: ${metrics['avg_loss']:.2f}
- Profit Factor: {metrics['profit_factor']:.2f}

Scan Interval: {self.config.scan_interval} seconds
Last Scan: {self.gui.last_scan_time.strftime('%Y-%m-%d %H:%M:%S')}

This tool monitors Webull log files to calculate
daily P&L for day trading without interfering
with Webull's operation.

Time-Based Averaging: {self.config.timeframe_minutes} minutes
Use Average Pricing: {"Enabled" if self.config.use_average_pricing else "Disabled"}
"""
            
            # Create a dialog
            info_window = tk.Toplevel(self.gui.root)
            info_window.title("Information")
            info_window.geometry("400x500")
            info_window.resizable(False, False)
            info_window.transient(self.gui.root)
            info_window.grab_set()
            
            # Style the dialog
            info_window.config(background=self.config.background_color)
            
            # Create header
            header_frame = tk.Frame(info_window, background=self.config.primary_color, height=40)
            header_frame.pack(fill=tk.X, padx=0, pady=0)
            
            header_label = tk.Label(
                header_frame, 
                text="Application Information",
                font=("Segoe UI", 12, "bold"),
                foreground="white",
                background=self.config.primary_color,
                padx=10,
                pady=10
            )
            header_label.pack(side=tk.LEFT)
            
            # Add content
            content_frame = tk.Frame(info_window, background=self.config.background_color)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            info_label = tk.Label(
                content_frame,
                text=info_text,
                font=("Segoe UI", 10),
                justify=tk.LEFT,
                background=self.config.background_color,
                foreground=self.config.text_color,
                wraplength=360
            )
            info_label.pack(fill=tk.BOTH)
            
            # Add button frame
            button_frame = tk.Frame(content_frame, background=self.config.background_color)
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            # Add buttons
            browse_button = self.create_modern_button(
                button_frame, "Browse Logs", self.browse_log_folder, width=10
            )
            browse_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            export_button = self.create_modern_button(
                button_frame, "Export Data", self.save_trade_data, width=10
            )
            export_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            reset_button = self.create_modern_button(
                button_frame, "Reset Data", self.reset_data, width=10
            )
            reset_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Add close button
            close_button_frame = tk.Frame(info_window, background=self.config.background_color)
            close_button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            close_button = self.create_modern_button(
                close_button_frame, "Close", info_window.destroy, width=10
            )
            close_button.pack(side=tk.RIGHT, pady=5)
            
        except Exception as e:
            logger.error(f"Error showing info dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to show information: {str(e)}")
    
    def show_settings_dialog(self):
        """Display settings dialog."""
        try:
            # COMPLETELY REDESIGNED FIXED SETTINGS DIALOG
            # Create settings dialog with explicit size
            settings_window = tk.Toplevel(self.gui.root)
            settings_window.title("Settings")
            settings_window.geometry("550x450")  # Smaller fixed height to ensure buttons are visible
            settings_window.minsize(550, 450)  # Enforce minimum size to keep buttons visible
            settings_window.resizable(True, True)
            settings_window.transient(self.gui.root)
            settings_window.grab_set()
            
            # Style the dialog
            settings_window.config(background=self.config.background_color)
            
            # Create a main container frame that will hold everything
            main_container = tk.Frame(settings_window, background=self.config.background_color)
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # Create header
            header_frame = tk.Frame(main_container, background=self.config.primary_color, height=40)
            header_frame.pack(fill=tk.X, padx=0, pady=0)
            
            header_label = tk.Label(
                header_frame, 
                text="Settings",
                font=("Segoe UI", 12, "bold"),
                foreground="white",
                background=self.config.primary_color,
                padx=10,
                pady=10
            )
            header_label.pack(side=tk.LEFT)
            
            # Content area - scrollable if needed
            content_container = tk.Frame(main_container, background=self.config.background_color)
            content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Button area - at the very bottom of the main container, separate from content
            bottom_area = tk.Frame(main_container, background=self.config.background_color, height=80)
            bottom_area.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
            
            # Create a separator for visual clarity
            separator = ttk.Separator(bottom_area, orient='horizontal')
            separator.pack(fill=tk.X, padx=0, pady=5)
            
            # Button frame inside bottom area
            button_frame = tk.Frame(bottom_area, background=self.config.background_color, height=40)
            button_frame.pack(fill=tk.X, padx=0, pady=5)
            
            # Variables to store settings
            settings_vars = {
                'log_folder': tk.StringVar(value=self.config.log_folder),
                'scan_interval': tk.IntVar(value=self.config.scan_interval),
                'auto_start': tk.BooleanVar(value=self.config.auto_start),
                'minimize_tray': tk.BooleanVar(value=self.config.minimize_to_tray),
                'dark_mode': tk.BooleanVar(value=self.config.dark_mode),
                'use_average_pricing': tk.BooleanVar(value=self.config.use_average_pricing),
                'minute_based_avg': tk.BooleanVar(value=self.config.minute_based_avg),
                'timeframe_minutes': tk.IntVar(value=self.config.timeframe_minutes)
            }
            
            # Create tabs in the content area
            notebook = ttk.Notebook(content_container)
            notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # 1. General Tab
            general_tab = self.create_general_settings_tab(notebook, settings_vars)
            notebook.add(general_tab, text="General")
            
            # 2. Trading Tab
            trading_tab = self.create_trading_settings_tab(notebook, settings_vars)
            notebook.add(trading_tab, text="Trading")
            
            # 3. Appearance Tab
            appearance_tab = self.create_appearance_settings_tab(notebook, settings_vars)
            notebook.add(appearance_tab, text="Appearance")
            
            # Create a direct save_settings function for this dialog
            def on_save_settings():
                self.direct_save_settings(settings_vars, settings_window)
            
            # Save Button - placed at bottom-right
            save_button = tk.Button(
                button_frame,
                text="SAVE SETTINGS",
                font=("Segoe UI", 10, "bold"),
                background="#4CAF50",
                foreground="white",
                activebackground="#45a049",
                activeforeground="white",
                relief=tk.RAISED,
                borderwidth=2,
                padx=15,
                pady=5,
                command=on_save_settings
            )
            save_button.pack(side=tk.RIGHT, padx=10, pady=5)
            
            # Cancel Button - placed next to Save
            cancel_button = tk.Button(
                button_frame,
                text="Cancel",
                font=("Segoe UI", 10),
                background=self.config.primary_color,
                foreground="white",
                activebackground=self.config.primary_color,
                activeforeground="white",
                relief=tk.FLAT,
                width=10,
                command=settings_window.destroy
            )
            cancel_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # Add protocol handler for window close (X button)
            settings_window.protocol("WM_DELETE_WINDOW", settings_window.destroy)
            
        except Exception as e:
            logger.error(f"Error showing settings dialog: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to show settings: {str(e)}")
    
    def create_general_settings_tab(self, parent, settings_vars):
        """Create the general settings tab"""
        general_tab = tk.Frame(parent, background=self.config.background_color)
        
        # Log Folder
        tk.Label(general_tab, text="Log Folder:", background=self.config.background_color, foreground=self.config.text_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        log_folder_entry = tk.Entry(general_tab, textvariable=settings_vars['log_folder'], width=40)
        log_folder_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        browse_button = self.create_modern_button(
            general_tab, 
            "Browse", 
            lambda: self.browse_folder_dialog(settings_vars['log_folder']), 
            width=8
        )
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Scan Interval
        tk.Label(general_tab, text="Scan Interval (seconds):", background=self.config.background_color, foreground=self.config.text_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        scan_interval_entry = tk.Entry(general_tab, textvariable=settings_vars['scan_interval'], width=5)
        scan_interval_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Auto start checkbox
        auto_start_check = tk.Checkbutton(
            general_tab, 
            text="Start monitoring automatically", 
            variable=settings_vars['auto_start'], 
            background=self.config.background_color, 
            foreground=self.config.text_color,
            selectcolor=self.config.background_color if self.config.dark_mode else None
        )
        auto_start_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Minimize to tray checkbox
        minimize_tray_check = tk.Checkbutton(
            general_tab, 
            text="Minimize to system tray", 
            variable=settings_vars['minimize_tray'], 
            background=self.config.background_color, 
            foreground=self.config.text_color,
            selectcolor=self.config.background_color if self.config.dark_mode else None
        )
        minimize_tray_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        return general_tab
    
    def create_trading_settings_tab(self, parent, settings_vars):
        """Create the trading settings tab"""
        trading_tab = tk.Frame(parent, background=self.config.background_color)
        
        # Use average pricing checkbox
        use_avg_pricing_check = tk.Checkbutton(
            trading_tab, 
            text="Use average pricing for profitability calculation", 
            variable=settings_vars['use_average_pricing'], 
            background=self.config.background_color, 
            foreground=self.config.text_color,
            selectcolor=self.config.background_color if self.config.dark_mode else None
        )
        use_avg_pricing_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Time frame selection
        tk.Label(
            trading_tab, 
            text="Time frame for average pricing (minutes):", 
            background=self.config.background_color, 
            foreground=self.config.text_color
        ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        timeframe_combobox = ttk.Combobox(
            trading_tab, 
            textvariable=settings_vars['timeframe_minutes'], 
            values=[1, 5, 10, 15, 30, 60], 
            width=5,
            state="readonly"
        )
        timeframe_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Add help text for time-based averaging
        timeframe_help = tk.Label(
            trading_tab, 
            text="When using average pricing, trades within the same time frame are grouped together. "
                 "The profitability of a trade is determined by comparing the average buy price to "
                 "the average sell price within that time frame.",
            background=self.config.background_color, 
            foreground=self.config.text_color,
            justify=tk.LEFT,
            wraplength=400
        )
        timeframe_help.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 10))
        
        # Minute-based averaging checkbox
        minute_based_avg_check = tk.Checkbutton(
            trading_tab, 
            text="Use minute-based price averaging", 
            variable=settings_vars['minute_based_avg'], 
            background=self.config.background_color, 
            foreground=self.config.text_color,
            selectcolor=self.config.background_color if self.config.dark_mode else None
        )
        minute_based_avg_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(15, 5))
        
        # Add help text for minute-based averaging
        minute_based_help = tk.Label(
            trading_tab, 
            text="Minute-based averaging groups trades by minute and calculates P&L using average prices within each minute. "
                 "This affects the actual P&L calculations, not just the profitability determination.",
            background=self.config.background_color, 
            foreground=self.config.text_color,
            justify=tk.LEFT,
            wraplength=400
        )
        minute_based_help.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 10))
        
        return trading_tab
    
    def create_appearance_settings_tab(self, parent, settings_vars):
        """Create the appearance settings tab"""
        appearance_tab = tk.Frame(parent, background=self.config.background_color)
        appearance_frame = tk.Frame(appearance_tab, background=self.config.background_color)
        appearance_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a canvas with scrollbar for the appearance tab
        canvas = tk.Canvas(appearance_frame, bg=self.config.background_color, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar to the canvas
        scrollbar = ttk.Scrollbar(appearance_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Create a frame inside the canvas to hold all appearance settings
        appearance_settings = tk.Frame(canvas, background=self.config.background_color)
        canvas.create_window((0, 0), window=appearance_settings, anchor="nw")
        
        # Dark mode option
        dark_mode_check = tk.Checkbutton(
            appearance_settings, 
            text="Dark Mode", 
            variable=settings_vars['dark_mode'], 
            background=self.config.background_color, 
            foreground=self.config.text_color,
            selectcolor=self.config.background_color if self.config.dark_mode else None
        )
        dark_mode_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="Primary Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        primary_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.primary_color,
            command=lambda: self.choose_color("primary_color")
        )
        primary_color_button.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="Background Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        bg_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.background_color,
            command=lambda: self.choose_color("background_color")
        )
        bg_color_button.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="PnL Panel Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        pnl_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.pnl_bg_color,
            command=lambda: self.choose_color("pnl_bg_color")
        )
        pnl_color_button.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="Text Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        
        text_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.text_color,
            command=lambda: self.choose_color("text_color")
        )
        text_color_button.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="Profit Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        
        profit_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.profit_colors[3],
            command=lambda: self.choose_color("profit_color")
        )
        profit_color_button.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(appearance_settings, text="Loss Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        
        loss_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.loss_colors[3],
            command=lambda: self.choose_color("loss_color")
        )
        loss_color_button.grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Metric color scale section
        color_scale_label = tk.Label(
            appearance_settings, 
            text="Metric Color Scale:",
            font=("Segoe UI", 10, "bold"),
            background=self.config.background_color,
            foreground=self.config.text_color
        )
        color_scale_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(15, 5))
        
        # Min (Bad) color
        tk.Label(appearance_settings, text="Bad (1):", background=self.config.background_color, foreground=self.config.text_color).grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        
        min_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.metric_colors[0],  # 1st color
            command=lambda: self.choose_color("color_scale_min")
        )
        min_color_button.grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Mid (Neutral) color
        tk.Label(appearance_settings, text="Neutral (5):", background=self.config.background_color, foreground=self.config.text_color).grid(row=9, column=0, sticky=tk.W, padx=5, pady=5)
        
        mid_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.metric_colors[4],  # 5th color
            command=lambda: self.choose_color("color_scale_mid")
        )
        mid_color_button.grid(row=9, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Max (Good) color
        tk.Label(appearance_settings, text="Good (10):", background=self.config.background_color, foreground=self.config.text_color).grid(row=10, column=0, sticky=tk.W, padx=5, pady=5)
        
        max_color_button = tk.Button(
            appearance_settings, 
            text="      ", 
            background=self.config.metric_colors[9],  # 10th color
            command=lambda: self.choose_color("color_scale_max")
        )
        max_color_button.grid(row=10, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Reset colors button
        reset_button = self.create_modern_button(appearance_settings, "Reset to Defaults", self.reset_colors, width=15)
        reset_button.grid(row=11, column=0, columnspan=2, sticky=tk.W, padx=5, pady=15)
        
        return appearance_tab
    
    def direct_save_settings(self, settings_vars, dialog):
        """
        Direct method to save settings from the dialog.
        This is a completely rewritten version to fix the issues.
        
        Args:
            settings_vars: Dictionary of setting variables
            dialog: Dialog window to close
        """
        try:
            logger.info("Starting direct_save_settings")
            
            # Extract all values from settings_vars
            log_folder = settings_vars['log_folder'].get()
            
            # CRITICAL FIX: Wrap these in try/except to ensure proper conversion
            try:
                scan_interval = int(settings_vars['scan_interval'].get())
                if scan_interval < 1:
                    raise ValueError("Scan interval must be at least 1 second.")
            except (ValueError, TypeError) as e:
                messagebox.showerror("Invalid Input", f"Scan interval error: {str(e)}")
                return False
                
            try:
                timeframe_minutes = int(settings_vars['timeframe_minutes'].get())
                if timeframe_minutes < 1 or timeframe_minutes > 60:
                    raise ValueError("Time frame must be between 1 and 60 minutes.")
            except (ValueError, TypeError) as e:
                messagebox.showerror("Invalid Input", f"Time frame error: {str(e)}")
                return False
            
            # Get boolean values directly from the BooleanVar objects
            auto_start = settings_vars['auto_start'].get()
            minimize_tray = settings_vars['minimize_tray'].get()
            dark_mode = settings_vars['dark_mode'].get()
            minute_based_avg = settings_vars['minute_based_avg'].get()
            use_average_pricing = settings_vars['use_average_pricing'].get()
            
            # DEBUG: Log the actual values being saved
            logger.info(f"Values to save: use_average_pricing={use_average_pricing} (type={type(use_average_pricing).__name__})")
            logger.info(f"Values to save: timeframe_minutes={timeframe_minutes} (type={type(timeframe_minutes).__name__})")
            logger.info(f"Values to save: minute_based_avg={minute_based_avg} (type={type(minute_based_avg).__name__})")
            
            # Check if any trading setting has changed
            trading_settings_changed = (
                self.config.use_average_pricing != use_average_pricing or
                self.config.minute_based_avg != minute_based_avg or
                self.config.timeframe_minutes != timeframe_minutes
            )
            
            # Create settings dictionary
            settings = {
                'log_folder': log_folder,
                'scan_interval': scan_interval,
                'auto_start': auto_start,
                'minimize_to_tray': minimize_tray,
                'dark_mode': dark_mode,
                'minute_based_avg': minute_based_avg,
                'use_average_pricing': use_average_pricing,
                'timeframe_minutes': timeframe_minutes
            }
            
            # Log the settings being saved
            logger.info(f"Settings to save: {settings}")
            
            # Directly update the config attributes for each setting
            self.config.log_folder = log_folder
            self.config.scan_interval = scan_interval 
            self.config.auto_start = auto_start
            self.config.minimize_to_tray = minimize_tray
            self.config.dark_mode = dark_mode
            self.config.minute_based_avg = minute_based_avg
            self.config.use_average_pricing = use_average_pricing
            self.config.timeframe_minutes = timeframe_minutes
            
            # Save the config to disk - important to save before proceeding
            result = self.config.save_config()
            
            if not result:
                logger.error("Failed to save config file!")
                messagebox.showerror("Error", "Failed to save settings. See log for details.")
                return False
                
            # Verify the settings were actually saved
            test_config = configparser.ConfigParser()
            test_config.read(CONFIG_FILE)
            
            if 'Settings' in test_config:
                saved_use_avg = test_config.get('Settings', 'use_average_pricing', fallback='MISSING')
                saved_timeframe = test_config.get('Settings', 'timeframe_minutes', fallback='MISSING')
                
                logger.info(f"Verification: use_average_pricing={saved_use_avg}, timeframe_minutes={saved_timeframe}")
                
                if saved_use_avg == 'MISSING' or saved_timeframe == 'MISSING':
                    logger.error("Verification failed! Settings not saved to file.")
                    messagebox.showerror("Error", "Settings verification failed. Some settings were not saved properly.")
                    return False
            else:
                logger.error("Verification failed! Settings section missing in config file.")
                messagebox.showerror("Error", "Settings verification failed. Settings section missing in config file.")
                return False
            
            # Update the UI
            self.gui.apply_theme()
            
            # Update log parser settings directly
            self.gui.log_parser.log_folder = log_folder
            
            # Log confirmation
            logger.info("Settings saved successfully via direct method")
            
            # IMPORTANT NEW CODE: Force recalculation of metrics if trading settings changed
            if trading_settings_changed:
                logger.info("Trading settings changed - recalculating metrics")
                
                # Recalculate metrics with existing trade pairs but new settings
                if hasattr(self.gui, 'trades') and hasattr(self.gui, 'trade_pairs') and self.gui.trades:
                    # Match trade pairs using FIFO with new settings
                    original_trade_pairs = self.gui.log_parser.match_buy_sell_trades(self.gui.trades)
                    
                    # Apply the appropriate pricing strategy based on new configuration
                    if self.config.use_average_pricing:
                        if self.config.timeframe_minutes <= 1:
                            # If timeframe is 1 minute or less, use minute-based pricing
                            trade_pairs = self.gui.analytics.apply_minute_based_pricing(original_trade_pairs)
                            logger.info("Recalculating with minute-based pricing")
                        else:
                            # Otherwise use the configured time frame
                            trade_pairs = self.gui.analytics.apply_timeframe_based_pricing(
                                original_trade_pairs, 
                                self.config.timeframe_minutes
                            )
                            logger.info(f"Recalculating with {self.config.timeframe_minutes}-minute timeframe pricing")
                    else:
                        # Use original FIFO trade pairs without averaging
                        trade_pairs = original_trade_pairs
                        logger.info("Recalculating with standard FIFO matching (no averaging)")
                    
                    # Store new trade pairs
                    self.gui.trade_pairs = trade_pairs
                    
                    # Calculate updated metrics
                    metrics = self.gui.analytics.calculate_advanced_metrics(trade_pairs)
                    
                    # Update the GUI with new metrics
                    self.gui.update_gui(
                        metrics_dict=metrics,
                        trades=self.gui.trades,
                        trade_pairs=trade_pairs,
                        position_warnings=self.gui.log_parser.position_warnings,
                        is_running=self.gui.running,
                        last_scan_time=self.gui.last_scan_time
                    )
            
            # Close the dialog
            dialog.destroy()
            
            # Show confirmation
            messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
            return True
                
        except Exception as e:
            logger.error(f"Error in direct_save_settings: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            return False
    
    def browse_folder_dialog(self, string_var):
        """
        Open dialog to browse for folder and update StringVar.
        
        Args:
            string_var: StringVar to update with selected folder
        """
        folder = filedialog.askdirectory(
            title="Select Folder",
            initialdir=string_var.get() if string_var.get() and os.path.exists(string_var.get()) else os.path.expanduser("~")
        )
        
        if folder:
            string_var.set(folder)
    
    def choose_color(self, color_name):
        """
        Open color chooser dialog and update the specified color.
        
        Args:
            color_name: Name of color to update
        """
        try:
            # Get current color based on name
            current_color = None
            
            if color_name == "primary_color":
                current_color = self.config.primary_color
            elif color_name == "background_color":
                current_color = self.config.background_color
            elif color_name == "pnl_bg_color":
                current_color = self.config.pnl_bg_color
            elif color_name == "text_color":
                current_color = self.config.text_color
            elif color_name == "profit_color":
                current_color = self.config.profit_colors[3]
            elif color_name == "loss_color":
                current_color = self.config.loss_colors[3]
            elif color_name == "color_scale_min":
                current_color = self.config.config.get('MetricColors', 'color_scale_min')
            elif color_name == "color_scale_mid":
                current_color = self.config.config.get('MetricColors', 'color_scale_mid')
            elif color_name == "color_scale_max":
                current_color = self.config.config.get('MetricColors', 'color_scale_max')
            
            # Open color chooser
            color = colorchooser.askcolor(initialcolor=current_color, title=f"Choose {color_name.replace('_', ' ').title()}")
            
            # If cancel was pressed, color will be None
            if color[1] is None:
                return
                
            # Update the color in config
            theme = 'DarkTheme' if self.config.dark_mode else 'LightTheme'
            
            # Update the color based on name
            if color_name == "primary_color":
                self.config.primary_color = color[1]
                self.config.config[theme]['primary_color'] = color[1]
            elif color_name == "background_color":
                self.config.background_color = color[1]
                self.config.config[theme]['background_color'] = color[1]
            elif color_name == "pnl_bg_color":
                self.config.pnl_bg_color = color[1]
                self.config.config[theme]['pnl_bg_color'] = color[1]
            elif color_name == "text_color":
                self.config.text_color = color[1]
                self.config.config[theme]['text_color'] = color[1]
            elif color_name == "profit_color":
                base_color = color[1]
                self.config.profit_colors = [
                    self.config.lighten_color(base_color, 0.8),  # Very light
                    self.config.lighten_color(base_color, 0.5),  # Light
                    self.config.lighten_color(base_color, 0.2),  # Medium
                    base_color,                                 # Normal
                    self.config.darken_color(base_color, 0.2)   # Dark
                ]
                self.config.config[theme]['profit_color'] = base_color
            elif color_name == "loss_color":
                base_color = color[1]
                self.config.loss_colors = [
                    self.config.lighten_color(base_color, 0.8),  # Very light
                    self.config.lighten_color(base_color, 0.5),  # Light
                    self.config.lighten_color(base_color, 0.2),  # Medium
                    base_color,                                 # Normal
                    self.config.darken_color(base_color, 0.2)   # Dark
                ]
                self.config.config[theme]['loss_color'] = base_color
            elif color_name == "color_scale_min":
                self.config.config['MetricColors']['color_scale_min'] = color[1]
                self.config.initialize_metric_color_scale()
            elif color_name == "color_scale_mid":
                self.config.config['MetricColors']['color_scale_mid'] = color[1]
                self.config.initialize_metric_color_scale()
            elif color_name == "color_scale_max":
                self.config.config['MetricColors']['color_scale_max'] = color[1]
                self.config.initialize_metric_color_scale()
            
            # Apply the theme
            self.gui.apply_theme()
                
        except Exception as e:
            logger.error(f"Error choosing color: {str(e)}")
            logger.error(traceback.format_exc())
    
    def reset_colors(self):
        """Reset colors to defaults."""
        self.config.reset_colors()
        self.gui.apply_theme()
        messagebox.showinfo("Colors Reset", "Colors have been reset to defaults. Save settings to apply permanently.")
    
    def browse_log_folder(self):
        """Open dialog to select log folder."""
        try:
            folder = filedialog.askdirectory(
                title="Select Webull Log Folder",
                initialdir=self.config.log_folder if os.path.exists(self.config.log_folder) else os.path.expanduser("~")
            )
            
            if folder:
                # Update config
                self.config.log_folder = folder
                self.config.save_config()
                
                # Update log parser
                self.gui.log_parser.log_folder = folder
                
                # Reset tracking state
                self.gui.log_parser.reset()
                
                # Show confirmation
                messagebox.showinfo("Log Folder", f"Log folder set to:\n{folder}")
                
                # Trigger reset callback if available
                if hasattr(self.gui, 'on_reset_callback') and callable(self.gui.on_reset_callback):
                    self.gui.on_reset_callback()
                
        except Exception as e:
            logger.error(f"Error browsing for log folder: {str(e)}")
            messagebox.showerror("Error", f"Failed to set log folder: {str(e)}")
    
    def reset_data(self):
        """Reset all trade data and start fresh."""
        try:
            # Confirm reset
            if messagebox.askyesno("Reset Data", "Reset all trade data and start fresh?"):
                # Reset log parser
                self.gui.log_parser.reset()
                
                # Reset analytics
                self.gui.analytics.reset_metrics()
                
                # Trigger reset callback if available
                if hasattr(self.gui, 'on_reset_callback') and callable(self.gui.on_reset_callback):
                    self.gui.on_reset_callback()
                
                # Update GUI
                self.gui.update_gui(self.gui.analytics.get_metrics_dict())
                
                logger.info("Trade data reset")
        except Exception as e:
            logger.error(f"Error resetting data: {str(e)}")
            messagebox.showerror("Error", f"Failed to reset data: {str(e)}")
    
    def save_trade_data(self):
        """Save current trade data to file."""
        try:
            # Implementation will be provided in the next update
            messagebox.showinfo("Not Implemented", "Export functionality will be implemented in the next version.")
        except Exception as e:
            logger.error(f"Error saving trade data: {str(e)}")
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")
    
    def show_trade_tagging_dialog(self, trades, trade_pairs):
        """Display trade tagging dialog."""
        messagebox.showinfo("Not Implemented", "Trade tagging will be implemented in the next version.")
        
    def show_journal_dialog(self):
        """Display trading journal dialog."""
        try:
            # Create the journal dialog window
            journal_window = tk.Toplevel(self.gui.root)
            journal_window.title("Trading Journal")
            journal_window.geometry("700x500")
            journal_window.resizable(True, True)
            journal_window.transient(self.gui.root)
            journal_window.grab_set()
            
            # Style the dialog
            journal_window.config(background=self.config.background_color)
            
            # Create header
            header_frame = tk.Frame(journal_window, background=self.config.primary_color, height=40)
            header_frame.pack(fill=tk.X, padx=0, pady=0)
            
            header_label = tk.Label(
                header_frame, 
                text="Trading Journal",
                font=("Segoe UI", 12, "bold"),
                foreground="white",
                background=self.config.primary_color,
                padx=10,
                pady=10
            )
            header_label.pack(side=tk.LEFT)
            
            # Add export journal button to header
            export_button = tk.Button(
                header_frame,
                text="Export",
                font=("Segoe UI", 9),
                background=self.config.accent_color,
                foreground="white",
                activebackground=self.config.accent_color,
                activeforeground="white",
                relief=tk.FLAT,
                padx=10,
                command=lambda: self.export_journal_entries(journal_window)
            )
            export_button.pack(side=tk.RIGHT, padx=10, pady=5)
            
            # Main content frame
            main_frame = tk.Frame(journal_window, background=self.config.background_color)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Date selection frame
            date_frame = tk.Frame(main_frame, background=self.config.background_color)
            date_frame.pack(fill=tk.X, pady=(0, 10))
            
            tk.Label(
                date_frame,
                text="Date:",
                font=("Segoe UI", 10, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(side=tk.LEFT, padx=(0, 10))
            
            # Date entry (default to today)
            date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
            date_entry = tk.Entry(
                date_frame,
                textvariable=date_var,
                font=("Segoe UI", 10),
                width=12
            )
            date_entry.pack(side=tk.LEFT, padx=(0, 10))
            
            # Load button
            load_button = self.create_modern_button(
                date_frame,
                "Load",
                lambda: self.load_journal_entry(date_var.get(), entry_text, mood_var, lessons_text, mistakes_text, wins_text, rating_var),
                width=8
            )
            load_button.pack(side=tk.LEFT, padx=5)
            
            # Journal entry frame
            entry_frame = tk.LabelFrame(
                main_frame,
                text="Journal Entry",
                font=("Segoe UI", 10, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color,
                padx=10,
                pady=10
            )
            entry_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Main journal entry text
            entry_text = tk.Text(
                entry_frame,
                font=("Segoe UI", 10),
                wrap=tk.WORD,
                height=8
            )
            entry_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Additional fields frame
            fields_frame = tk.Frame(entry_frame, background=self.config.background_color)
            fields_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Left column
            left_col = tk.Frame(fields_frame, background=self.config.background_color)
            left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            
            # Mood
            tk.Label(
                left_col,
                text="Today's Mood (1-5):",
                font=("Segoe UI", 9, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(anchor=tk.W)
            
            mood_var = tk.IntVar(value=3)
            mood_scale = tk.Scale(
                left_col,
                from_=1,
                to=5,
                orient=tk.HORIZONTAL,
                variable=mood_var,
                background=self.config.background_color,
                foreground=self.config.text_color,
                font=("Segoe UI", 8)
            )
            mood_scale.pack(fill=tk.X, pady=(0, 10))
            
            # Rating
            tk.Label(
                left_col,
                text="Overall Day Rating (1-5):",
                font=("Segoe UI", 9, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(anchor=tk.W)
            
            rating_var = tk.IntVar(value=3)
            rating_scale = tk.Scale(
                left_col,
                from_=1,
                to=5,
                orient=tk.HORIZONTAL,
                variable=rating_var,
                background=self.config.background_color,
                foreground=self.config.text_color,
                font=("Segoe UI", 8)
            )
            rating_scale.pack(fill=tk.X)
            
            # Right column
            right_col = tk.Frame(fields_frame, background=self.config.background_color)
            right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            # Lessons learned
            tk.Label(
                right_col,
                text="Lessons Learned:",
                font=("Segoe UI", 9, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(anchor=tk.W)
            
            lessons_text = tk.Text(
                right_col,
                font=("Segoe UI", 9),
                wrap=tk.WORD,
                height=3
            )
            lessons_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            
            # Mistakes
            tk.Label(
                right_col,
                text="Mistakes Made:",
                font=("Segoe UI", 9, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(anchor=tk.W)
            
            mistakes_text = tk.Text(
                right_col,
                font=("Segoe UI", 9),
                wrap=tk.WORD,
                height=3
            )
            mistakes_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            
            # Wins/Successes
            tk.Label(
                right_col,
                text="Wins/Successes:",
                font=("Segoe UI", 9, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            ).pack(anchor=tk.W)
            
            wins_text = tk.Text(
                right_col,
                font=("Segoe UI", 9),
                wrap=tk.WORD,
                height=3
            )
            wins_text.pack(fill=tk.BOTH, expand=True)
            
            # Button frame
            button_frame = tk.Frame(main_frame, background=self.config.background_color)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Save button
            save_button = tk.Button(
                button_frame,
                text="SAVE ENTRY",
                font=("Segoe UI", 10, "bold"),
                background="#4CAF50",
                foreground="white",
                activebackground="#45a049",
                activeforeground="white",
                relief=tk.RAISED,
                borderwidth=2,
                padx=15,
                pady=5,
                command=lambda: self.save_journal_entry_from_dialog(
                    date_var.get(),
                    entry_text.get("1.0", tk.END).strip(),
                    mood_var.get(),
                    lessons_text.get("1.0", tk.END).strip(),
                    mistakes_text.get("1.0", tk.END).strip(),
                    wins_text.get("1.0", tk.END).strip(),
                    rating_var.get(),
                    journal_window
                )
            )
            save_button.pack(side=tk.RIGHT, padx=10)
            
            # Close button
            close_button = self.create_modern_button(
                button_frame,
                "Close",
                journal_window.destroy,
                width=10
            )
            close_button.pack(side=tk.RIGHT, padx=5)
            
            # Load today's entry if it exists
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.load_journal_entry(today_str, entry_text, mood_var, lessons_text, mistakes_text, wins_text, rating_var)
            
        except Exception as e:
            logger.error(f"Error showing journal dialog: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to show journal dialog: {str(e)}")
    
    def load_journal_entry(self, date_str, entry_text, mood_var, lessons_text, mistakes_text, wins_text, rating_var):
        """
        Load a journal entry for the specified date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            entry_text: Text widget for main entry
            mood_var: IntVar for mood
            lessons_text: Text widget for lessons
            mistakes_text: Text widget for mistakes
            wins_text: Text widget for wins
            rating_var: IntVar for rating
        """
        try:
            # Validate date format
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format")
                return
            
            # Load entry from database
            entry = get_journal_entry(date_str)
            
            if entry:
                # Clear existing content
                entry_text.delete("1.0", tk.END)
                lessons_text.delete("1.0", tk.END)
                mistakes_text.delete("1.0", tk.END)
                wins_text.delete("1.0", tk.END)
                
                # Populate fields
                entry_text.insert("1.0", entry.get('entry', ''))
                mood_var.set(entry.get('mood', 3))
                lessons_text.insert("1.0", entry.get('lessons', ''))
                mistakes_text.insert("1.0", entry.get('mistakes', ''))
                wins_text.insert("1.0", entry.get('wins', ''))
                rating_var.set(entry.get('rating', 3))
                
                logger.info(f"Loaded journal entry for {date_str}")
            else:
                # Clear all fields for new entry
                entry_text.delete("1.0", tk.END)
                lessons_text.delete("1.0", tk.END)
                mistakes_text.delete("1.0", tk.END)
                wins_text.delete("1.0", tk.END)
                mood_var.set(3)
                rating_var.set(3)
                
                logger.info(f"No journal entry found for {date_str} - cleared form for new entry")
                
        except Exception as e:
            logger.error(f"Error loading journal entry: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to load journal entry: {str(e)}")
    
    def save_journal_entry_from_dialog(self, date_str, entry, mood, lessons, mistakes, wins, rating, dialog_window):
        """
        Save a journal entry from the dialog form.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            entry: Main journal entry text
            mood: Mood rating (1-5)
            lessons: Lessons learned text
            mistakes: Mistakes made text
            wins: Wins/successes text
            rating: Overall day rating (1-5)
            dialog_window: Dialog window reference
        """
        try:
            # Validate date format
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format")
                return
            
            # Validate required field
            if not entry.strip():
                messagebox.showerror("Missing Entry", "Please enter a journal entry")
                return
            
            # Save to database
            success = save_journal_entry(
                date=date_str,
                entry=entry,
                mood=mood,
                lessons=lessons,
                mistakes=mistakes,
                wins=wins,
                rating=rating
            )
            
            if success:
                messagebox.showinfo("Success", f"Journal entry saved for {date_str}")
                logger.info(f"Saved journal entry for {date_str}")
            else:
                messagebox.showerror("Error", "Failed to save journal entry")
                
        except Exception as e:
            logger.error(f"Error saving journal entry: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to save journal entry: {str(e)}")
    
    def export_journal_entries(self, parent_window):
        """
        Export journal entries with the export functionality from journal_integration.
        
        Args:
            parent_window: Parent window for the export operation
        """
        try:
            # Add the journal export script to the parent window
            # This will add an export button that downloads a JSON file
            export_script = get_journal_export_script()
            
            # Create a simple info dialog explaining the export process
            messagebox.showinfo(
                "Export Journal Entries",
                "Journal entries are automatically exported when you save them through the web interface.\n\n"
                "To manually export entries:\n"
                "1. Use the calendar web interface\n"
                "2. Click 'Save All Journal Entries to Database'\n"
                "3. The entries will be downloaded as a JSON file\n"
                "4. The file will be automatically imported on next program start"
            )
            
        except Exception as e:
            logger.error(f"Error exporting journal entries: {str(e)}")
            messagebox.showerror("Error", f"Failed to export journal entries: {str(e)}")

# Version and metadata
VERSION = "2.8"
CREATED_DATE = "2025-05-07 10:45:00"
LAST_MODIFIED = "2025-05-24 12:00:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_gui_components",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - GUI Components Module - v2.8
# Created: 2025-05-07 10:45:00
# Last Modified: 2025-05-24 12:00:00
# webull_realtime_gui_components.py