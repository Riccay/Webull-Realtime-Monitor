"""
Webull Realtime P&L Monitor - GUI Components Module - v2.0
Created: 2025-05-07 10:45:00
Last Modified: 2025-05-10 17:00:00

This module provides specialized GUI components for the Webull Realtime P&L Monitor.
It handles dialogs, charts, and other complex UI elements.
"""

import os
import sys
import time
import logging
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd

# Import from common module
from webull_realtime_common import logger, TRADES_DIR

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
        self.version = "2.0"
        self.created_date = "2025-05-07 10:45:00"
        self.modified_date = "2025-05-10 17:00:00"
        
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
                profits = df[df['PnL'] > 0]
                losses = df[df['PnL'] < 0]
                
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

Minute-Based Averaging: {"Enabled" if self.config.minute_based_avg else "Disabled"}
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
            # Create settings dialog
            settings_window = tk.Toplevel(self.gui.root)
            settings_window.title("Settings")
            settings_window.geometry("550x500")  # Increased height to ensure all elements are visible
            settings_window.resizable(True, True)
            settings_window.transient(self.gui.root)
            settings_window.grab_set()
            
            # Style the dialog
            settings_window.config(background=self.config.background_color)
            
            # Create header
            header_frame = tk.Frame(settings_window, background=self.config.primary_color, height=40)
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
            
            # Create notebook for tabbed interface
            notebook = ttk.Notebook(settings_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # General tab
            general_tab = tk.Frame(notebook, background=self.config.background_color)
            notebook.add(general_tab, text="General")
            
            # Appearance tab
            appearance_tab = tk.Frame(notebook, background=self.config.background_color)
            notebook.add(appearance_tab, text="Appearance")
            
            # Add settings to General tab
            tk.Label(general_tab, text="Log Folder:", background=self.config.background_color, foreground=self.config.text_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            
            log_folder_var = tk.StringVar(value=self.config.log_folder)
            log_folder_entry = tk.Entry(general_tab, textvariable=log_folder_var, width=40)
            log_folder_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            browse_button = self.create_modern_button(general_tab, "Browse", lambda: self.browse_folder_dialog(log_folder_var), width=8)
            browse_button.grid(row=0, column=2, padx=5, pady=5)
            
            tk.Label(general_tab, text="Scan Interval (seconds):", background=self.config.background_color, foreground=self.config.text_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            
            scan_interval_var = tk.IntVar(value=self.config.scan_interval)
            scan_interval_entry = tk.Entry(general_tab, textvariable=scan_interval_var, width=5)
            scan_interval_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Auto start checkbox
            auto_start_var = tk.BooleanVar(value=self.config.auto_start)
            auto_start_check = tk.Checkbutton(general_tab, text="Start monitoring automatically", variable=auto_start_var, 
                                             background=self.config.background_color, foreground=self.config.text_color,
                                             selectcolor=self.config.background_color if self.config.dark_mode else None)
            auto_start_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Minimize to tray checkbox
            minimize_tray_var = tk.BooleanVar(value=self.config.minimize_to_tray)
            minimize_tray_check = tk.Checkbutton(general_tab, text="Minimize to system tray", variable=minimize_tray_var, 
                                                background=self.config.background_color, foreground=self.config.text_color,
                                                selectcolor=self.config.background_color if self.config.dark_mode else None)
            minimize_tray_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Minute-based averaging checkbox
            minute_based_avg_var = tk.BooleanVar(value=self.config.minute_based_avg)
            minute_based_avg_check = tk.Checkbutton(general_tab, text="Use minute-based price averaging", variable=minute_based_avg_var, 
                                                   background=self.config.background_color, foreground=self.config.text_color,
                                                   selectcolor=self.config.background_color if self.config.dark_mode else None)
            minute_based_avg_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Add help text for minute-based averaging
            minute_based_help = tk.Label(
                general_tab, 
                text="Minute-based averaging groups trades by minute and calculates P&L using average prices within each minute.",
                background=self.config.background_color, 
                foreground=self.config.text_color,
                justify=tk.LEFT,
                wraplength=400
            )
            minute_based_help.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 10))
            
            # Add settings to Appearance tab
            # Dark mode option
            dark_mode_var = tk.BooleanVar(value=self.config.dark_mode)
            dark_mode_check = tk.Checkbutton(appearance_tab, text="Dark Mode", variable=dark_mode_var, 
                                            background=self.config.background_color, foreground=self.config.text_color,
                                            selectcolor=self.config.background_color if self.config.dark_mode else None)
            dark_mode_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="Primary Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            
            primary_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.primary_color,
                command=lambda: self.choose_color("primary_color")
            )
            primary_color_button.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="Background Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
            
            bg_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.background_color,
                command=lambda: self.choose_color("background_color")
            )
            bg_color_button.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="PnL Panel Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
            
            pnl_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.pnl_bg_color,
                command=lambda: self.choose_color("pnl_bg_color")
            )
            pnl_color_button.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="Text Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
            
            text_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.text_color,
                command=lambda: self.choose_color("text_color")
            )
            text_color_button.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="Profit Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
            
            profit_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.profit_colors[3],
                command=lambda: self.choose_color("profit_color")
            )
            profit_color_button.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
            
            tk.Label(appearance_tab, text="Loss Color:", background=self.config.background_color, foreground=self.config.text_color).grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
            
            loss_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.loss_colors[3],
                command=lambda: self.choose_color("loss_color")
            )
            loss_color_button.grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Metric color scale section
            color_scale_label = tk.Label(
                appearance_tab, 
                text="Metric Color Scale:",
                font=("Segoe UI", 10, "bold"),
                background=self.config.background_color,
                foreground=self.config.text_color
            )
            color_scale_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(15, 5))
            
            # Min (Bad) color
            tk.Label(appearance_tab, text="Bad (1):", background=self.config.background_color, foreground=self.config.text_color).grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
            
            min_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.metric_colors[0],  # 1st color
                command=lambda: self.choose_color("color_scale_min")
            )
            min_color_button.grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Mid (Neutral) color
            tk.Label(appearance_tab, text="Neutral (5):", background=self.config.background_color, foreground=self.config.text_color).grid(row=9, column=0, sticky=tk.W, padx=5, pady=5)
            
            mid_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.metric_colors[4],  # 5th color
                command=lambda: self.choose_color("color_scale_mid")
            )
            mid_color_button.grid(row=9, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Max (Good) color
            tk.Label(appearance_tab, text="Good (10):", background=self.config.background_color, foreground=self.config.text_color).grid(row=10, column=0, sticky=tk.W, padx=5, pady=5)
            
            max_color_button = tk.Button(
                appearance_tab, 
                text="      ", 
                background=self.config.metric_colors[9],  # 10th color
                command=lambda: self.choose_color("color_scale_max")
            )
            max_color_button.grid(row=10, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Reset colors button
            reset_button = self.create_modern_button(appearance_tab, "Reset to Defaults", self.reset_colors, width=15)
            reset_button.grid(row=11, column=0, columnspan=2, sticky=tk.W, padx=5, pady=15)
            
            # Add buttons at the bottom - ENHANCED VISIBILITY
            button_frame = tk.Frame(settings_window, background=self.config.background_color, height=50)
            button_frame.pack(fill=tk.X, padx=10, pady=15)  # Increased padding
            
            # Create a separator for visual clarity
            separator = ttk.Separator(settings_window, orient='horizontal')
            separator.pack(fill=tk.X, padx=10, pady=5)
            
            # Enhanced Save button with better visibility
            save_button = tk.Button(
                button_frame,
                text="SAVE SETTINGS",
                font=("Segoe UI", 10, "bold"),
                background="#4CAF50",  # Bright green - highly visible
                foreground="white",
                activebackground="#45a049",
                activeforeground="white",
                relief=tk.RAISED,
                borderwidth=2,
                padx=15,
                pady=5,
                command=lambda: self.save_settings(
                    log_folder_var.get(),
                    scan_interval_var.get(),
                    auto_start_var.get(),
                    minimize_tray_var.get(),
                    dark_mode_var.get(),
                    minute_based_avg_var.get(),
                    settings_window
                )
            )
            save_button.pack(side=tk.RIGHT, padx=10, pady=5)
            
            cancel_button = self.create_modern_button(
                button_frame, "Cancel", 
                settings_window.destroy,
                width=10
            )
            cancel_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
        except Exception as e:
            logger.error(f"Error showing settings dialog: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to show settings: {str(e)}")
    
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
    
    def save_settings(self, log_folder, scan_interval, auto_start, minimize_tray, dark_mode, minute_based_avg, dialog):
        """
        Save settings and close the dialog.
        
        Args:
            log_folder: Log folder path
            scan_interval: Scan interval in seconds
            auto_start: Whether to auto-start monitoring
            minimize_tray: Whether to minimize to tray
            dark_mode: Whether to use dark mode
            minute_based_avg: Whether to use minute-based price averaging
            dialog: Dialog window to close
        """
        try:
            # Validate scan interval
            try:
                scan_interval = int(scan_interval)
                if scan_interval < 1:
                    raise ValueError("Scan interval must be at least 1 second.")
            except ValueError as ve:
                messagebox.showerror("Invalid Input", str(ve))
                return
                
            # Update settings
            settings = {
                'log_folder': log_folder,
                'scan_interval': scan_interval,
                'auto_start': auto_start,
                'minimize_to_tray': minimize_tray,
                'dark_mode': dark_mode,
                'minute_based_avg': minute_based_avg
            }
            
            # Log settings for debugging
            logger.info(f"Saving settings: {settings}")
            
            # Update config
            if self.config.update_settings(settings):
                # Update the UI
                self.gui.apply_theme()
                
                # Update log parser settings directly
                self.gui.log_parser.log_folder = log_folder
                
                # Log confirmation
                logger.info(f"Settings updated")
                
                # Close the dialog
                dialog.destroy()
                
                # Show confirmation
                messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
            else:
                messagebox.showerror("Error", "Failed to save settings.")
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
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

# Version and metadata
VERSION = "2.0"
CREATED_DATE = "2025-05-07 10:45:00"
LAST_MODIFIED = "2025-05-10 17:00:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_gui_components",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - GUI Components Module - v2.0
# Created: 2025-05-07 10:45:00
# Last Modified: 2025-05-10 17:00:00
# webull_realtime_gui_components.py