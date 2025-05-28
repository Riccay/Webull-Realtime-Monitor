"""
Webull Realtime P&L Monitor - Configuration Module - v2.3
Created: 2025-05-06 15:00:00
Last Modified: 2025-05-28 14:30:00

This module handles configuration management for the Webull Realtime P&L Monitor.
It provides functions for loading, saving, and managing application settings.
"""

import os
import configparser
import logging
import traceback

# Import from common module
from webull_realtime_common import (
    logger, CONFIG_FILE, lighten_color, darken_color, 
    hex_to_rgb, rgb_to_hex, detect_webull_log_folder,
    blend_colors
)

class WebullConfig:
    """Configuration manager for Webull Realtime P&L Monitor."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        # Version info
        self.version = "2.3"
        self.created_date = "2025-05-06 15:00:00"
        self.modified_date = "2025-05-28 08:30:00"
        
        # Create config parser
        self.config = configparser.ConfigParser()
        
        # CRITICAL: Load config FIRST before setting any default values
        self.load_config()
        
        # Now initialize attributes FROM the config
        # This is the key fix - load from config first, then use defaults as fallback
        self.scan_interval = self.config.getint('Settings', 'scan_interval', fallback=10)
        self.log_folder = self.config.get('Settings', 'log_folder', fallback='')
        self.auto_start = self._str_to_bool(self.config.get('Settings', 'auto_start', fallback='True'))
        self.minimize_to_tray = self._str_to_bool(self.config.get('Settings', 'minimize_to_tray', fallback='False'))
        self.dark_mode = self._str_to_bool(self.config.get('Settings', 'dark_mode', fallback='False'))
        self.minute_based_avg = self._str_to_bool(self.config.get('Settings', 'minute_based_avg', fallback='True'))
        self.use_average_pricing = self._str_to_bool(self.config.get('Settings', 'use_average_pricing', fallback='True'))
        self.timeframe_minutes = self.config.getint('Settings', 'timeframe_minutes', fallback=5)
        self.backup_rotation_count = self.config.getint('Settings', 'backup_rotation_count', fallback=50)
        
        # Log loaded values immediately after loading
        logger.info(f"STARTUP - Settings loaded directly from {CONFIG_FILE}:")
        logger.info(f"  - scan_interval: {self.scan_interval}")
        logger.info(f"  - use_average_pricing: {self.use_average_pricing}")
        logger.info(f"  - timeframe_minutes: {self.timeframe_minutes}")
        logger.info(f"  - minute_based_avg: {self.minute_based_avg}")
        
        # Now initialize theme colors and UI elements
        # Theme colors - initialize default values
        self.primary_color = "#2c3e50"  # Default primary color
        self.background_color = "#ecf0f1"  # Default background color
        self.pnl_bg_color = "#34495e"  # Default PnL panel color
        self.text_color = "#333333"  # Default text color
        self.accent_color = "#3498db"  # Default accent color
        self.profit_colors = []
        self.loss_colors = []
        self.neutral_color = "#9e9e9e"
        
        # New metric color scale
        self.metric_colors = []
        self.metric_ranges = {}
        
        # Load theme colors
        self.load_theme_colors()
        
        # Initialize metric color scale
        self.initialize_metric_color_scale()
        
        # Initialize metric ranges
        self.initialize_metric_ranges()
        
        # If log folder not set or not found, try to detect it
        if not self.log_folder or not os.path.exists(self.log_folder):
            self.log_folder = detect_webull_log_folder()
            
    def _str_to_bool(self, value):
        """
        Convert string value to boolean.
        
        Args:
            value (str): String value to convert
            
        Returns:
            bool: Converted boolean value
        """
        if isinstance(value, bool):
            return value
            
        return value.lower() in ('true', 'yes', '1', 'y', 't')
            
    def load_config(self):
        """Load application configuration from file."""
        try:
            logger.info(f"Attempting to load config from: {CONFIG_FILE}")
            
            # Ensure config directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            # Create default config if it doesn't exist
            if not os.path.exists(CONFIG_FILE):
                logger.info(f"Config file not found at {CONFIG_FILE}, creating default")
                self._create_default_config()
            else:
                # Load existing config
                logger.info(f"Loading existing config from {CONFIG_FILE}")
                self.config.read(CONFIG_FILE)
                
                # Check if the existing config has the necessary sections
                if 'Settings' not in self.config or 'LightTheme' not in self.config:
                    logger.warning("Config file exists but missing essential sections. Will add defaults.")
                    self._ensure_config_sections()
                
                # Debug output the loaded settings
                if 'Settings' in self.config:
                    logger.info("Loaded settings from file:")
                    for key, value in self.config['Settings'].items():
                        logger.info(f"  {key} = {value}")
                else:
                    logger.warning("No Settings section found in config file!")
                    
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Set up minimal default configuration
            self._create_default_config(minimal=True)
            
    def _create_default_config(self, minimal=False):
        """
        Create default configuration.
        
        Args:
            minimal (bool): Whether to create a minimal configuration
        """
        # Settings - all values are strings in the config
        self.config['Settings'] = {
            'scan_interval': '10',
            'log_folder': '',
            'auto_start': 'True',
            'minimize_to_tray': 'False',
            'dark_mode': 'False',
            'minute_based_avg': 'True',
            'use_average_pricing': 'True',  # Default to using average pricing
            'timeframe_minutes': '5',  # Default time frame in minutes
            'backup_rotation_count': '50',  # Default number of journal backups to keep
            'version': self.version,
            'created_date': self.created_date,
            'modified_date': self.modified_date
        }
        
        if not minimal:
            # Default light theme colors
            self.config['LightTheme'] = {
                'primary_color': '#2c3e50',
                'background_color': '#ecf0f1',
                'pnl_bg_color': '#34495e',
                'profit_color': '#2ecc71',
                'loss_color': '#e74c3c',
                'text_color': '#333333',
                'accent_color': '#3498db'
            }
            
            # Default dark theme colors
            self.config['DarkTheme'] = {
                'primary_color': '#1e272e',
                'background_color': '#2d3436',
                'pnl_bg_color': '#1e272e',
                'profit_color': '#2ecc71',
                'loss_color': '#e74c3c',
                'text_color': '#ecf0f1',
                'accent_color': '#00a8ff'
            }
            
            # Display settings
            self.config['Display'] = {
                'window_width': '600',
                'window_height': '650',
                'font_size': '10',
                'chart_height': '300'
            }
            
            # Metric color scale settings
            self.config['MetricColors'] = {
                'color_scale_min': '#e74c3c',  # Red for bad metrics
                'color_scale_mid': '#f39c12',  # Yellow for medium metrics
                'color_scale_max': '#2ecc71'   # Green for good metrics
            }
            
            # Save the default config
            self.save_config()
        
    def _ensure_config_sections(self):
        """Ensure all required config sections and options exist."""
        # Add any missing sections
        if 'Settings' not in self.config:
            self.config['Settings'] = {}
        if 'LightTheme' not in self.config:
            self.config['LightTheme'] = {}
        if 'DarkTheme' not in self.config:
            self.config['DarkTheme'] = {}
        if 'Display' not in self.config:
            self.config['Display'] = {}
        if 'MetricColors' not in self.config:
            self.config['MetricColors'] = {}
        
        # Check and set default values if options are missing
        # Settings
        settings_defaults = {
            'scan_interval': '10',
            'log_folder': '',
            'auto_start': 'True',
            'minimize_to_tray': 'False',
            'dark_mode': 'False',
            'minute_based_avg': 'True',
            'use_average_pricing': 'True',
            'timeframe_minutes': '5',
            'backup_rotation_count': '50',
            'version': self.version,
            'created_date': self.created_date,
            'modified_date': self.modified_date
        }
        
        for key, value in settings_defaults.items():
            if key not in self.config['Settings']:
                self.config['Settings'][key] = value
        
        # Light theme defaults
        light_defaults = {
            'primary_color': '#2c3e50',
            'background_color': '#ecf0f1',
            'pnl_bg_color': '#34495e',
            'profit_color': '#2ecc71',
            'loss_color': '#e74c3c',
            'text_color': '#333333',
            'accent_color': '#3498db'
        }
        
        for key, value in light_defaults.items():
            if key not in self.config['LightTheme']:
                self.config['LightTheme'][key] = value
        
        # Dark theme defaults
        dark_defaults = {
            'primary_color': '#1e272e',
            'background_color': '#2d3436',
            'pnl_bg_color': '#1e272e',
            'profit_color': '#2ecc71',
            'loss_color': '#e74c3c',
            'text_color': '#ecf0f1',
            'accent_color': '#00a8ff'
        }
        
        for key, value in dark_defaults.items():
            if key not in self.config['DarkTheme']:
                self.config['DarkTheme'][key] = value
        
        # Metric color scale defaults
        metric_color_defaults = {
            'color_scale_min': '#e74c3c',  # Red for bad metrics
            'color_scale_mid': '#f39c12',  # Yellow for medium metrics
            'color_scale_max': '#2ecc71'   # Green for good metrics
        }
        
        for key, value in metric_color_defaults.items():
            if key not in self.config['MetricColors']:
                self.config['MetricColors'][key] = value
        
        # Display defaults
        display_defaults = {
            'window_width': '600',
            'window_height': '650',
            'font_size': '10',
            'chart_height': '300'
        }
        
        for key, value in display_defaults.items():
            if key not in self.config['Display']:
                self.config['Display'][key] = value
        
        # Save updated config
        self.save_config()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Make sure all attributes exist before saving
            if not hasattr(self, 'scan_interval'):
                self.scan_interval = 10
            if not hasattr(self, 'log_folder'):
                self.log_folder = ''
            if not hasattr(self, 'auto_start'):
                self.auto_start = True
            if not hasattr(self, 'minimize_to_tray'):
                self.minimize_to_tray = False
            if not hasattr(self, 'dark_mode'):
                self.dark_mode = False
            if not hasattr(self, 'minute_based_avg'):
                self.minute_based_avg = True
            if not hasattr(self, 'use_average_pricing'):
                self.use_average_pricing = True
            if not hasattr(self, 'timeframe_minutes'):
                self.timeframe_minutes = 5
            if not hasattr(self, 'backup_rotation_count'):
                self.backup_rotation_count = 50
                
            # Update config with current values
            self.config['Settings']['scan_interval'] = str(self.scan_interval)
            self.config['Settings']['log_folder'] = self.log_folder
            self.config['Settings']['auto_start'] = str(self.auto_start)
            self.config['Settings']['minimize_to_tray'] = str(self.minimize_to_tray)
            self.config['Settings']['dark_mode'] = str(self.dark_mode)
            self.config['Settings']['minute_based_avg'] = str(self.minute_based_avg)
            self.config['Settings']['use_average_pricing'] = str(self.use_average_pricing)
            self.config['Settings']['timeframe_minutes'] = str(self.timeframe_minutes)
            self.config['Settings']['backup_rotation_count'] = str(self.backup_rotation_count)
            self.config['Settings']['version'] = self.version
            self.config['Settings']['created_date'] = self.created_date
            self.config['Settings']['modified_date'] = self.modified_date
            
            # Log settings that are about to be saved
            logger.info(f"Saving settings to {CONFIG_FILE}")
            logger.info(f"Settings to save: scan_interval={self.scan_interval}, "
                      f"use_average_pricing={self.use_average_pricing}, "
                      f"timeframe_minutes={self.timeframe_minutes}, "
                      f"minute_based_avg={self.minute_based_avg}, "
                      f"auto_start={self.auto_start}")
            
            # Ensure config directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            # Validate config has the necessary sections before saving
            if 'Settings' not in self.config:
                logger.error("Settings section missing from config! Creating it.")
                self.config['Settings'] = {}
                self._ensure_config_sections()
            
            # Save to file
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
                
            # Verify file was saved correctly
            if os.path.exists(CONFIG_FILE):
                file_size = os.path.getsize(CONFIG_FILE)
                logger.info(f"Configuration saved successfully. File size: {file_size} bytes")
                
                # Read back and verify settings were saved correctly
                test_config = configparser.ConfigParser()
                test_config.read(CONFIG_FILE)
                
                if 'Settings' in test_config:
                    saved_use_avg = test_config.get('Settings', 'use_average_pricing', fallback='MISSING')
                    saved_timeframe = test_config.get('Settings', 'timeframe_minutes', fallback='MISSING')
                    logger.info(f"Verification: use_average_pricing={saved_use_avg}, timeframe_minutes={saved_timeframe}")
                    
                    if saved_use_avg == 'MISSING' or saved_timeframe == 'MISSING':
                        logger.error("Verification failed! Some settings are missing after save.")
                else:
                    logger.error("Verification failed! Settings section missing after save.")
            else:
                logger.error(f"Verification failed! Config file not found after save attempt.")
                
            logger.debug(f"Configuration settings - auto_start: {self.auto_start}, use_average_pricing: {self.use_average_pricing}, timeframe_minutes: {self.timeframe_minutes}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            logger.error(traceback.format_exc())
            logger.error(f"Current state - scan_interval: {getattr(self, 'scan_interval', 'N/A')}")
            return False
            
    def load_theme_colors(self):
        """Load theme colors based on dark mode setting."""
        try:
            # Determine theme based on dark mode setting
            theme = 'DarkTheme' if self.dark_mode else 'LightTheme'
            
            # Load basic colors from config
            self.primary_color = self.config.get(theme, 'primary_color')
            self.background_color = self.config.get(theme, 'background_color')
            self.pnl_bg_color = self.config.get(theme, 'pnl_bg_color')
            self.text_color = self.config.get(theme, 'text_color')
            self.accent_color = self.config.get(theme, 'accent_color')
            
            # Base profit and loss colors
            profit_base = self.config.get(theme, 'profit_color')
            loss_base = self.config.get(theme, 'loss_color')
            
            # Define different shades of green for profit coloring
            self.profit_colors = [
                lighten_color(profit_base, 0.8),  # Very light green (entire window background)
                lighten_color(profit_base, 0.5),  # Light green
                lighten_color(profit_base, 0.2),  # Medium green
                profit_base,                      # Normal green
                darken_color(profit_base, 0.2)    # Dark green
            ]
            
            # Define different shades of red for loss coloring
            self.loss_colors = [
                lighten_color(loss_base, 0.8),  # Very light red (entire window background)
                lighten_color(loss_base, 0.5),  # Light red
                lighten_color(loss_base, 0.2),  # Medium red
                loss_base,                      # Normal red
                darken_color(loss_base, 0.2)    # Dark red
            ]
            
            # Neutral color
            self.neutral_color = "#9e9e9e" if not self.dark_mode else "#777777"
            
            # Load metric color scale colors
            self.initialize_metric_color_scale()
            
        except Exception as e:
            logger.error(f"Error loading theme colors: {str(e)}")
            self.set_default_theme_colors()
    
    def initialize_metric_color_scale(self):
        """Initialize metric color scale from 1-10."""
        try:
            # Get color scale colors from config
            min_color = self.config.get('MetricColors', 'color_scale_min', fallback='#e74c3c')
            mid_color = self.config.get('MetricColors', 'color_scale_mid', fallback='#f39c12')
            max_color = self.config.get('MetricColors', 'color_scale_max', fallback='#2ecc71')
            
            # Create 10-scale color gradient (1-10)
            # 1-5: Blend from min_color to mid_color
            # 6-10: Blend from mid_color to max_color
            self.metric_colors = [
                min_color,  # 1 (Worst)
                blend_colors(min_color, mid_color, 0.25),  # 2
                blend_colors(min_color, mid_color, 0.5),   # 3
                blend_colors(min_color, mid_color, 0.75),  # 4
                mid_color,  # 5 (Middle)
                blend_colors(mid_color, max_color, 0.2),   # 6
                blend_colors(mid_color, max_color, 0.4),   # 7
                blend_colors(mid_color, max_color, 0.6),   # 8
                blend_colors(mid_color, max_color, 0.8),   # 9
                max_color   # 10 (Best)
            ]
            
        except Exception as e:
            logger.error(f"Error initializing metric color scale: {str(e)}")
            # Set default color scale
            self.metric_colors = [
                '#e74c3c',  # 1 (Worst) - Red
                '#e67e22',  # 2
                '#f39c12',  # 3
                '#f5b041',  # 4
                '#f9e79f',  # 5 (Middle) - Yellow
                '#aed581',  # 6
                '#7cb342',  # 7
                '#558b2f',  # 8
                '#33691e',  # 9
                '#2ecc71'   # 10 (Best) - Green
            ]
    
    def initialize_metric_ranges(self):
        """Initialize min and max values for different metric types."""
        # Define ranges for different metrics (min, max)
        # These ranges determine how a value maps to the 1-10 color scale
        self.metric_ranges = {
            'profit_rate': (0, 100),                 # Percentage (0-100%)
            'avg_profit': (0, 5),                    # Dollars (0-$5)
            'avg_loss': (-5, 0),                     # Dollars (-$5-0)
            'profit_factor': (0, 10),                # Ratio (0-10)
            'sharpe_ratio': (0, 3),                  # Ratio (0-3)
            'max_drawdown': (5, 0),                  # Dollars inverted ($5-0)
            'avg_duration': (10, 0.5),               # Minutes inverted (10-0.5)
            'expectancy': (0, 5),                    # Dollars (0-$5)
            'consec_profits': (0, 10),               # Count (0-10)
            'consec_losses': (5, 0),                 # Count inverted (5-0)
            'max_consec_profits': (0, 10),           # Count (0-10)
            'max_consec_losses': (10, 0),            # Count inverted (10-0)
            'largest_profit': (0, 10),               # Dollars (0-$10)
            'largest_loss': (-5, 0),                 # Dollars (-$5-0)
            'profit_loss_ratio': (0, 5),             # Ratio (0-5)
            'std_dev': (5, 0)                        # Dollars inverted ($5-0)
        }
    
    def get_metric_color_scale(self, value, metric_type):
        """
        Get color from the 1-10 scale based on value and metric type.
        
        Args:
            value (float): Metric value
            metric_type (str): Type of metric (must be in metric_ranges)
            
        Returns:
            tuple: (color_hex, scale_value_1_to_10)
        """
        try:
            if metric_type not in self.metric_ranges:
                return self.neutral_color, 5  # Default middle value
                
            min_val, max_val = self.metric_ranges[metric_type]
            
            # For inverted ranges (where lower is better)
            inverted = min_val > max_val
            if inverted:
                min_val, max_val = max_val, min_val
                value = max_val - (value - min_val) if value > min_val else max_val
            
            # Clamp value to range
            value = max(min_val, min(value, max_val))
            
            # Calculate position in range (0-1)
            range_size = max_val - min_val
            if range_size == 0:
                position = 0.5  # Avoid division by zero
            else:
                position = (value - min_val) / range_size
            
            # Convert to 1-10 scale
            scale_value = int(position * 9) + 1  # 1-10
            scale_value = 1 if scale_value < 1 else 10 if scale_value > 10 else scale_value
            
            # Get corresponding color
            color = self.metric_colors[scale_value - 1]
            
            return color, scale_value
            
        except Exception as e:
            logger.error(f"Error getting metric color scale: {str(e)}")
            return self.neutral_color, 5  # Default middle value
    
    def set_default_theme_colors(self):
        """Set default theme colors if loading fails."""
        if self.dark_mode:
            self.primary_color = "#1e272e"
            self.background_color = "#2d3436"
            self.pnl_bg_color = "#1e272e"
            self.text_color = "#ecf0f1"
            self.accent_color = "#00a8ff"
        else:
            self.primary_color = "#2c3e50"
            self.background_color = "#ecf0f1"
            self.pnl_bg_color = "#34495e"
            self.text_color = "#333333"
            self.accent_color = "#3498db"
        
        # Default profit colors
        profit_base = "#2ecc71"
        self.profit_colors = [
            lighten_color(profit_base, 0.8),  # Very light green
            lighten_color(profit_base, 0.5),  # Light green
            lighten_color(profit_base, 0.2),  # Medium green
            profit_base,                      # Normal green
            darken_color(profit_base, 0.2)    # Dark green
        ]
        
        # Default loss colors
        loss_base = "#e74c3c"
        self.loss_colors = [
            lighten_color(loss_base, 0.8),  # Very light red
            lighten_color(loss_base, 0.5),  # Light red
            lighten_color(loss_base, 0.2),  # Medium red
            loss_base,                      # Normal red
            darken_color(loss_base, 0.2)    # Dark red
        ]
        
        # Neutral color
        self.neutral_color = "#9e9e9e" if not self.dark_mode else "#777777"
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        self.dark_mode = not self.dark_mode
        self.load_theme_colors()
        self.save_config()
        return self.dark_mode
        
    def reset_colors(self):
        """Reset colors to defaults based on current theme."""
        theme = 'DarkTheme' if self.dark_mode else 'LightTheme'
        
        # Default light theme colors
        light_defaults = {
            'primary_color': '#2c3e50',
            'background_color': '#ecf0f1',
            'pnl_bg_color': '#34495e',
            'profit_color': '#2ecc71',
            'loss_color': '#e74c3c',
            'text_color': '#333333',
            'accent_color': '#3498db'
        }
        
        # Default dark theme colors
        dark_defaults = {
            'primary_color': '#1e272e',
            'background_color': '#2d3436',
            'pnl_bg_color': '#1e272e',
            'profit_color': '#2ecc71',
            'loss_color': '#e74c3c',
            'text_color': '#ecf0f1',
            'accent_color': '#00a8ff'
        }
        
        # Default metric colors
        metric_defaults = {
            'color_scale_min': '#e74c3c',
            'color_scale_mid': '#f39c12',
            'color_scale_max': '#2ecc71'
        }
        
        # Set colors based on theme
        theme_defaults = dark_defaults if self.dark_mode else light_defaults
        self.config[theme] = theme_defaults
        self.config['MetricColors'] = metric_defaults
        
        # Reload theme colors
        self.load_theme_colors()
        
        # Save changes
        self.save_config()
    
    def update_settings(self, settings_dict):
        """
        Update settings from a dictionary.
        
        Args:
            settings_dict (dict): Dictionary of settings to update
        
        Returns:
            bool: True if settings were updated, False otherwise
        """
        try:
            # Log the incoming settings
            logger.info(f"Updating settings: {settings_dict}")
            
            # FIX: Improve boolean conversion
            def ensure_bool(value):
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'y', 't')
                # Integers or other non-zero values are considered True
                return bool(value)
                
            # Update each setting if provided
            if 'scan_interval' in settings_dict:
                try:
                    self.scan_interval = int(settings_dict['scan_interval'])
                    logger.info(f"Set scan_interval to {self.scan_interval}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid scan_interval value: {settings_dict['scan_interval']}")
                    logger.warning(f"Error: {str(e)}")
                    # Keep the current value
            
            if 'log_folder' in settings_dict:
                self.log_folder = settings_dict['log_folder']
                logger.info(f"Set log_folder to {self.log_folder}")
                
            if 'auto_start' in settings_dict:
                self.auto_start = ensure_bool(settings_dict['auto_start'])
                logger.info(f"Set auto_start to {self.auto_start}")
                
            if 'minimize_to_tray' in settings_dict:
                self.minimize_to_tray = ensure_bool(settings_dict['minimize_to_tray'])
                logger.info(f"Set minimize_to_tray to {self.minimize_to_tray}")
                
            if 'dark_mode' in settings_dict:
                old_dark_mode = self.dark_mode
                self.dark_mode = ensure_bool(settings_dict['dark_mode'])
                logger.info(f"Set dark_mode to {self.dark_mode}")
                
                # Reload theme colors if dark mode changed
                if old_dark_mode != self.dark_mode:
                    self.load_theme_colors()
            
            if 'minute_based_avg' in settings_dict:
                self.minute_based_avg = ensure_bool(settings_dict['minute_based_avg'])
                logger.info(f"Set minute_based_avg to {self.minute_based_avg}")
                
            if 'use_average_pricing' in settings_dict:
                self.use_average_pricing = ensure_bool(settings_dict['use_average_pricing'])
                logger.info(f"Set use_average_pricing to {self.use_average_pricing}")
                
            if 'timeframe_minutes' in settings_dict:
                # Ensure it's within valid range (1-60 minutes)
                try:
                    timeframe = int(settings_dict['timeframe_minutes'])
                    self.timeframe_minutes = max(1, min(60, timeframe))
                    logger.info(f"Set timeframe_minutes to {self.timeframe_minutes}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid timeframe_minutes value: {settings_dict['timeframe_minutes']}")
                    logger.warning(f"Error: {str(e)}")
                    # Keep the current value
            
            if 'backup_rotation_count' in settings_dict:
                # Ensure it's within valid range (5-500 backups)
                try:
                    backup_count = int(settings_dict['backup_rotation_count'])
                    self.backup_rotation_count = max(5, min(500, backup_count))
                    logger.info(f"Set backup_rotation_count to {self.backup_rotation_count}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid backup_rotation_count value: {settings_dict['backup_rotation_count']}")
                    logger.warning(f"Error: {str(e)}")
                    # Keep the current value
            
            # Log the updated settings
            logger.info(f"Settings updated - auto_start: {self.auto_start}, use_average_pricing: {self.use_average_pricing}, timeframe_minutes: {self.timeframe_minutes}")
            
            # Save changes
            if not self.save_config():
                logger.error("Failed to save config file")
                return False
            
            # Double-check settings were saved properly
            test_config = configparser.ConfigParser()
            test_config.read(CONFIG_FILE)
            
            if 'Settings' in test_config:
                saved_use_avg = test_config.get('Settings', 'use_average_pricing', fallback='MISSING')
                if saved_use_avg == 'MISSING':
                    logger.error("Settings verification failed! use_average_pricing not saved correctly.")
                    return False
            else:
                logger.error("Settings verification failed! Settings section missing.")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            logger.error(traceback.format_exc())
            return False

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_config",
        "version": "2.3",
        "created": "2025-05-06 15:00:00",
        "modified": "2025-05-28 08:30:00"
    }

# Webull Realtime P&L Monitor - Configuration Module - v2.2
# Created: 2025-05-06 15:00:00
# Last Modified: 2025-05-23 08:15:00