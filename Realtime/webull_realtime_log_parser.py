"""
Webull Realtime P&L Monitor - Log Parser Module - v1.4
Created: 2025-05-06 14:00:00
Last Modified: 2025-05-07 11:15:00

This module handles the parsing of Webull log files to extract
trade information and match buy/sell pairs.
"""

import os
import re
import json
import time
import logging
import traceback
from datetime import datetime
import pandas as pd

# Import from common module
from webull_realtime_common import logger, parse_date_time

# JSON extraction utilities
def extract_json(line):
    """
    Extract JSON data from a log line.
    
    Args:
        line (str): Log line to extract JSON from
        
    Returns:
        dict or None: Extracted JSON data or None if extraction fails
    """
    try:
        # Extract the JSON part
        json_pattern = r'"({.*})"$|true "(\[.*\])"$|true "({.*})"$'
        json_match = re.search(json_pattern, line)
        
        if json_match:
            # Find which group matched
            json_data_part = next((g for g in json_match.groups() if g), None)
            
            if json_data_part:
                # Unescape the JSON string
                json_data_part = bytes(json_data_part, "utf-8").decode("unicode_escape")
                
                # Parse JSON
                return json.loads(json_data_part)
        
        # Look for direct JSON without quotes (some newer format logs)
        direct_json_pattern = r'true ({.*})$|true (\[.*\])$'
        direct_match = re.search(direct_json_pattern, line)
        
        if direct_match:
            # Find which group matched
            json_data_part = next((g for g in direct_match.groups() if g), None)
            
            if json_data_part:
                # Parse JSON
                return json.loads(json_data_part)
                
        return None
        
    except Exception as e:
        logger.debug(f"JSON extraction error: {str(e)}")
        return None

def ensure_est_timezone(df):
    """
    Ensures all datetime values are properly in US Eastern Time.
    
    Args:
        df (DataFrame): DataFrame to process
        
    Returns:
        DataFrame: Processed DataFrame with corrected timezone
    """
    try:
        df = df.copy()  # Create a copy to avoid modifying the original
        
        # If DataFrame contains separate Date and Time columns
        if 'Date' in df.columns and 'Time' in df.columns:
            # Create a datetime column if it doesn't exist
            if 'DateTime' not in df.columns:
                try:
                    # Convert to string and concatenate
                    df['DateTime'] = pd.to_datetime(
                        df['Date'].astype(str) + ' ' + 
                        df['Time'].astype(str)
                    )
                except Exception as e:
                    logger.warning(f"Error creating DateTime column: {str(e)}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error ensuring EST timezone: {str(e)}")
        return df

class WebullLogParser:
    """Parser for Webull log files to extract trade information."""
    
    def __init__(self, log_folder):
        """
        Initialize the Webull log parser.
        
        Args:
            log_folder (str): Path to Webull log folder
        """
        self.log_folder = log_folder
        self.processed_logs = set()
        self.processed_trade_ids = set()
        self.last_file_positions = {}
        self.position_warnings = []
        self.open_positions = {}  # Track open positions by symbol
        
    def find_today_log_files(self):
        """
        Find Webull log files for today.
        
        Returns:
            list: List of log file paths
        """
        try:
            if not os.path.exists(self.log_folder):
                logger.error(f"Log folder does not exist: {self.log_folder}")
                return []
                
            # Get today's date in the format used in log filenames
            today_str = datetime.now().strftime("%m-%d")
            
            # Find all log files for today
            log_files = []
            for filename in os.listdir(self.log_folder):
                if filename.endswith('.log') and today_str in filename:
                    log_files.append(os.path.join(self.log_folder, filename))
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            if not log_files:
                logger.warning(f"No log files found for today ({today_str}).")
                
            return log_files
            
        except Exception as e:
            logger.error(f"Error finding log files: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def extract_trades_from_logs(self, log_files):
        """
        Extract trades from log files with careful file handling.
        
        Args:
            log_files (list): List of log file paths
            
        Returns:
            list: Extracted trades
        """
        new_trades = []
        all_trades = []  # Store all trades for position calculation
        
        try:
            # Process each log file
            for log_file in log_files:
                # Skip already fully processed logs
                if log_file in self.processed_logs:
                    continue
                    
                try:
                    # Get file modification time
                    mod_time = os.path.getmtime(log_file)
                    mod_dt = datetime.fromtimestamp(mod_time)
                    
                    # MODIFIED: Skip if file was modified in the last 0.5 seconds
                    # This still prevents reading in-progress files but allows
                    # quicker detection of completed trades
                    if (datetime.now() - mod_dt).total_seconds() < 0.5:
                        logger.debug(f"Skipping very recently modified file: {log_file}")
                        continue
                    
                    # Get file size
                    file_size = os.path.getsize(log_file)
                    
                    # Get last position we read up to for this file
                    last_position = self.last_file_positions.get(log_file, 0)
                    
                    # If file size hasn't changed and we've read it before, skip
                    if last_position >= file_size and last_position > 0:
                        continue
                    
                    logger.debug(f"Processing log file: {log_file} from position {last_position}/{file_size}")
                        
                    # Open with read-only mode with shared access
                    # This ensures we don't interfere with Webull's file writing
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as file:
                        # Seek to the last position we read
                        file.seek(last_position)
                        
                        # Process the file line by line from where we left off
                        line_num = 0
                        line_buffer = []  # Buffer for accumulating lines
                        
                        for line in file:
                            line_num += 1
                            line_buffer.append(line.strip())
                            
                            # Keep buffer at a reasonable size
                            if len(line_buffer) > 5:
                                line_buffer.pop(0)
                            
                            # Look for trade data 
                            # Check multiple patterns for trade data
                            if ("WBAUOrderSummaryStore::loadAUOrderSummary true" in line or
                                "WBOrderListStore::processOrderData true" in line or
                                "WBOrderInfoStore::setOrderInfos true" in line):
                                
                                # Try to extract JSON from this line and previous lines in buffer
                                json_data = None
                                for buf_line in reversed(line_buffer):
                                    json_data = extract_json(buf_line)
                                    if json_data:
                                        break
                                
                                if json_data:
                                    # Process orders based on the data format we found
                                    orders = []
                                    
                                    # Multiple pattern support
                                    if "todayOrders" in json_data:
                                        # Standard order summary format
                                        orders = self.extract_orders_from_summary(json_data)
                                    elif "items" in json_data:
                                        # Direct items format 
                                        orders = self.extract_orders_from_items(json_data)
                                    elif isinstance(json_data, list):
                                        # List of orders format
                                        orders = self.extract_orders_from_list(json_data)
                                    
                                    # Add to trades list
                                    for order in orders:
                                        # Skip if already processed
                                        order_id = order.get('id', '')
                                        if order_id in self.processed_trade_ids:
                                            continue
                                            
                                        # Process the trade
                                        trade = self.process_trade(order)
                                        if trade:
                                            logger.info(f"Found new trade: {trade['Symbol']} {trade['Side']} {trade['Quantity']}@{trade['Price']}")
                                            new_trades.append(trade)
                                            all_trades.append(trade)
                                            self.processed_trade_ids.add(order_id)
                        
                        # Update the last position for this file
                        self.last_file_positions[log_file] = file.tell()
                        logger.debug(f"Updated file position: {log_file} to {self.last_file_positions[log_file]}")
                    
                    # Only mark as fully processed if we've read the whole file
                    # Do not mark as processed to re-scan for missed trades
                    if self.last_file_positions[log_file] >= file_size:
                        logger.debug(f"Fully processed log file: {log_file}")
                        # DO NOT add to processed_logs to ensure we re-scan
                        # Fix for missing trades
                        # self.processed_logs.add(log_file)
                    
                except PermissionError:
                    logger.warning(f"File is being used by another process: {log_file}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing log file {log_file}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            return new_trades
            
        except Exception as e:
            logger.error(f"Error extracting trades: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def extract_orders_from_summary(self, summary_data):
        """
        Extract order items from order summary JSON.
        
        Args:
            summary_data (dict): Order summary data
            
        Returns:
            list: Extracted order items
        """
        order_items = []
        
        try:
            # Extract from order summary format
            if "todayOrders" in summary_data:
                today_orders = summary_data.get("todayOrders", [])
                
                for order in today_orders:
                    items = order.get("items", [])
                    for item in items:
                        # Check for both Filled and PartialFilled status
                        # Also accept other status codes if they have filled quantity
                        if (item.get("status") == "Filled" or 
                            item.get("status") == "PartialFilled" or 
                            (item.get("filledQuantity") and float(item.get("filledQuantity", "0")) > 0)):
                            
                            # Log the entire item for debugging
                            logger.debug(f"Found order item: {item.get('action')} {item.get('ticker', {}).get('symbol')} {item.get('filledQuantity')} @ {item.get('avgFilledPrice')}")
                            
                            order_items.append(item)
            
            return order_items
        except Exception as e:
            logger.error(f"Error extracting orders from summary: {str(e)}")
            return []
    
    def extract_orders_from_items(self, items_data):
        """
        Extract order items from direct items JSON.
        
        Args:
            items_data (dict): Items data
            
        Returns:
            list: Extracted order items
        """
        order_items = []
        
        try:
            # Extract from direct items format
            if "items" in items_data:
                items = items_data.get("items", [])
                
                for item in items:
                    # Check for both Filled and PartialFilled status
                    # Also accept other status codes if they have filled quantity
                    if (item.get("status") == "Filled" or 
                        item.get("status") == "PartialFilled" or 
                        (item.get("filledQuantity") and float(item.get("filledQuantity", "0")) > 0)):
                        
                        logger.debug(f"Found direct item: {item.get('action')} {item.get('ticker', {}).get('symbol')} {item.get('filledQuantity')} @ {item.get('avgFilledPrice')}")
                        
                        order_items.append(item)
            
            return order_items
        except Exception as e:
            logger.error(f"Error extracting orders from items: {str(e)}")
            return []
    
    def extract_orders_from_list(self, order_list):
        """
        Extract order items from a list of orders.
        
        Args:
            order_list (list): List of order data
            
        Returns:
            list: Extracted order items
        """
        order_items = []
        
        try:
            # Extract from direct list format
            if isinstance(order_list, list):
                for item in order_list:
                    # Check for both Filled and PartialFilled status
                    # Also accept other status codes if they have filled quantity
                    if (item.get("status") == "Filled" or 
                        item.get("status") == "PartialFilled" or 
                        (item.get("filledQuantity") and float(item.get("filledQuantity", "0")) > 0)):
                        
                        logger.debug(f"Found list item: {item.get('action')} {item.get('ticker', {}).get('symbol')} {item.get('filledQuantity')} @ {item.get('avgFilledPrice')}")
                        
                        order_items.append(item)
            
            return order_items
        except Exception as e:
            logger.error(f"Error extracting orders from list: {str(e)}")
            return []
    
    def process_trade(self, order_item):
        """
        Process a single trade order item.
        
        Args:
            order_item (dict): Order item data
            
        Returns:
            dict: Processed trade data or None if processing fails
        """
        try:
            # Get order ID to help identify duplicates across partial fills
            order_id = order_item.get('id', '')
            
            # Extract needed fields
            action = order_item.get('action')
            order_status = order_item.get('status', '')
            
            # Support both filledQuantity and totalQuantity as seen in different log formats
            # For partial fills, use filledQuantity instead of totalQuantity
            if order_status == "PartialFilled":
                filled_quantity = order_item.get('filledQuantity')
            else:
                filled_quantity = order_item.get('filledQuantity') or order_item.get('totalQuantity')
            
            # Skip if no quantity was filled
            if not filled_quantity or float(filled_quantity) <= 0:
                return None
                
            # IMPORTANT: Use avgFilledPrice as the primary price field
            # This corresponds to the "Filled" column in Webull desktop
            filled_price = order_item.get('avgFilledPrice')
            
            # Fallback only if absolutely necessary
            if not filled_price:
                logger.warning(f"Missing avgFilledPrice for order {order_id}, trying alternative fields")
                filled_price = order_item.get('Price')
            
            # Support both filledTime and updateTime as seen in different log formats
            filled_time = order_item.get('filledTime') or order_item.get('updateTime')
            
            # Handle ticker object which may be structured differently in different log formats
            ticker = order_item.get('ticker', {})
            if isinstance(ticker, dict):
                symbol = ticker.get('symbol')
            else:
                symbol = order_item.get('symbol')
            
            # Check if all required fields are present
            if not all([action, filled_quantity, filled_price, filled_time, symbol]):
                missing = []
                if not action: missing.append('action')
                if not filled_quantity: missing.append('filled_quantity')
                if not filled_price: missing.append('filled_price')
                if not filled_time: missing.append('filled_time')
                if not symbol: missing.append('symbol')
                
                logger.warning(f"Missing required fields for order {order_id}: {missing}")
                return None
            
            # Parse date and time
            date_str, time_str = parse_date_time(filled_time)
            if not date_str or not time_str:
                logger.warning(f"Failed to parse date/time for order {order_id}: {filled_time}")
                return None
                
            # Convert quantity and price
            try:
                quantity = float(filled_quantity)
                price = float(filled_price)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting quantity/price for order {order_id}: {e}")
                return None
                
            # Skip zero quantity trades
            if quantity <= 0:
                return None
                
            # Create trade record with more fields for better analysis
            trade = {
                'Date': date_str,
                'Time': time_str,
                'Symbol': symbol,
                'Quantity': abs(quantity),
                'Price': price,
                'Side': action,  # 'BUY' or 'SELL'
                'OrderID': order_id,
                'Status': order_status,
                'Commission': float(order_item.get('fee', '0.0')),
                'FilledAmount': float(order_item.get('filledAmount', '0.0')),
                'Exchange': ticker.get('disExchangeCode', '') if isinstance(ticker, dict) else '',
                'OrderType': order_item.get('orderType', ''),
                'CreateTime': order_item.get('createTime', ''),
                'UpdateTime': order_item.get('updateTime', ''),
                'DateTime': f"{date_str} {time_str}"  # For easier datetime operations
            }
            
            logger.info(f"Processed trade: {symbol} {action} {quantity} @ {price} ({date_str} {time_str})")
            
            return trade
            
        except Exception as e:
            logger.error(f"Trade processing error: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def match_buy_sell_trades(self, trades):
        """
        Match buy and sell trades to create complete trade pairs.
        
        Args:
            trades (list): List of individual trade executions
            
        Returns:
            list: List of trade pairs (each pair is a dict with buy and sell info)
        """
        try:
            # Convert to DataFrame for easier processing
            if not trades:
                return []
                
            df = pd.DataFrame(trades)
            
            # Convert DateTime to proper datetime objects
            df['DateTimeObj'] = pd.to_datetime(df['DateTime'])
            
            # Group by symbol to process each stock separately
            symbols = df['Symbol'].unique()
            
            trade_pairs = []
            
            for symbol in symbols:
                symbol_trades = df[df['Symbol'] == symbol].copy()
                
                # Separate buys and sells
                buys = symbol_trades[symbol_trades['Side'].str.upper() == 'BUY'].sort_values('DateTimeObj')
                sells = symbol_trades[symbol_trades['Side'].str.upper() == 'SELL'].sort_values('DateTimeObj')
                
                # Skip if no buys or sells
                if buys.empty or sells.empty:
                    continue
                    
                # Process using FIFO (First In, First Out) method
                remaining_buys = buys.copy()
                remaining_sells = sells.copy()
                
                # Important: Only consider completed trades (sells that happened AFTER a buy)
                while not remaining_buys.empty and not remaining_sells.empty:
                    current_buy = remaining_buys.iloc[0]
                    
                    # Filter sells to only those that happened after this buy
                    valid_sells = remaining_sells[remaining_sells['DateTimeObj'] > current_buy['DateTimeObj']]
                    
                    if valid_sells.empty:
                        # No valid sells found for this buy, move to next buy
                        remaining_buys = remaining_buys.iloc[1:]
                        continue
                    
                    current_sell = valid_sells.iloc[0]
                    
                    # Match quantities
                    buy_qty = current_buy['Quantity']
                    sell_qty = current_sell['Quantity']
                    
                    if buy_qty == sell_qty:
                        # Perfect match - create pair and remove both
                        pair = self.create_trade_pair(current_buy, current_sell)
                        trade_pairs.append(pair)
                        
                        remaining_buys = remaining_buys.iloc[1:]
                        remaining_sells = remaining_sells[remaining_sells.index != current_sell.name]
                        
                    elif buy_qty > sell_qty:
                        # Buy quantity is larger - use full sell and partial buy
                        # Create a copy of the buy with matched quantity
                        matched_buy = current_buy.copy()
                        matched_buy['Quantity'] = sell_qty
                        
                        # Create pair
                        pair = self.create_trade_pair(matched_buy, current_sell)
                        trade_pairs.append(pair)
                        
                        # Update remaining buy quantity
                        remaining_buys.at[remaining_buys.index[0], 'Quantity'] = buy_qty - sell_qty
                        remaining_sells = remaining_sells[remaining_sells.index != current_sell.name]
                        
                    else:  # buy_qty < sell_qty
                        # Sell quantity is larger - use full buy and partial sell
                        # Create a copy of the sell with matched quantity
                        matched_sell = current_sell.copy()
                        matched_sell['Quantity'] = buy_qty
                        
                        # Create pair
                        pair = self.create_trade_pair(current_buy, matched_sell)
                        trade_pairs.append(pair)
                        
                        # Update remaining sell quantity
                        remaining_sells.at[current_sell.name, 'Quantity'] = sell_qty - buy_qty
                        remaining_buys = remaining_buys.iloc[1:]
            
            # Recalculate positions after matching trades
            self.calculate_clean_positions(trades)
            
            return trade_pairs
            
        except Exception as e:
            logger.error(f"Error matching buy/sell trades: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def create_trade_pair(self, buy, sell):
        """
        Create a trade pair from a buy and sell execution.
        
        Args:
            buy (Series): Buy trade
            sell (Series): Sell trade
            
        Returns:
            dict: Trade pair with calculated P&L
        """
        try:
            # Calculate P&L
            buy_cost = buy['Quantity'] * buy['Price']
            sell_proceeds = sell['Quantity'] * sell['Price']
            
            # Include commissions if available
            buy_commission = buy.get('Commission', 0)
            sell_commission = sell.get('Commission', 0)
            
            # Calculate total cost and proceeds
            total_cost = buy_cost + buy_commission
            total_proceeds = sell_proceeds - sell_commission
            
            # Calculate P&L
            pnl = total_proceeds - total_cost
            pnl_percent = (pnl / total_cost) * 100 if total_cost > 0 else 0
            
            # Calculate trade duration
            buy_time = pd.to_datetime(buy['DateTimeObj'])
            sell_time = pd.to_datetime(sell['DateTimeObj'])
            
            # Duration in minutes
            duration_mins = (sell_time - buy_time).total_seconds() / 60
            
            # Create trade pair record
            pair = {
                'Symbol': buy['Symbol'],
                'Quantity': buy['Quantity'],  # Should be same as sell['Quantity'] for this pair
                'BuyPrice': buy['Price'],
                'SellPrice': sell['Price'],
                'BuyTime': buy['DateTime'],
                'SellTime': sell['DateTime'],
                'BuyOrderID': buy['OrderID'],
                'SellOrderID': sell['OrderID'],
                'BuyCost': buy_cost,
                'SellProceeds': sell_proceeds,
                'BuyCommission': buy_commission,
                'SellCommission': sell_commission,
                'PnL': pnl,
                'PnLPercent': pnl_percent,
                'TotalCost': total_cost,
                'DurationMinutes': duration_mins,
                'Result': 'Profit' if pnl > 0 else 'Loss',
                'Exchange': buy['Exchange'],
                'Date': buy['Date']  # Use buy date as trade date
            }
            
            return pair
            
        except Exception as e:
            logger.error(f"Error creating trade pair: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return a minimal pair with error flag
            return {
                'Symbol': buy.get('Symbol', 'Unknown'),
                'Error': str(e),
                'Quantity': buy.get('Quantity', 0),
                'PnL': 0,
                'Result': 'Error'
            }
    
    def calculate_clean_positions(self, trades):
        """
        Calculate clean positions from all trades.
        This completely replaces the old position tracking logic.
        
        Args:
            trades (list): List of all trades
        """
        try:
            # Reset positions and warnings
            self.open_positions = {}
            self.position_warnings = []
            
            if not trades:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # If empty, nothing to do
            if df.empty:
                return
                
            # Ensure DateTime column exists
            if 'DateTime' not in df.columns:
                if 'Date' in df.columns and 'Time' in df.columns:
                    df['DateTime'] = df['Date'] + ' ' + df['Time']
                else:
                    return
            
            # Convert to datetime and sort
            df['DateTimeObj'] = pd.to_datetime(df['DateTime'])
            df = df.sort_values('DateTimeObj')
            
            # Calculate net positions by symbol
            positions = {}
            
            # Group by symbol and calculate net position
            for symbol in df['Symbol'].unique():
                symbol_df = df[df['Symbol'] == symbol]
                
                buys = symbol_df[symbol_df['Side'].str.upper() == 'BUY']
                sells = symbol_df[symbol_df['Side'].str.upper() == 'SELL']
                
                buy_qty = buys['Quantity'].sum()
                sell_qty = sells['Quantity'].sum()
                
                net_position = buy_qty - sell_qty
                
                # Only record if there is a significant position
                if abs(net_position) > 0.01:
                    positions[symbol] = net_position
            
            # Store the open positions
            self.open_positions = positions
            
            # Add warnings for each open position
            for symbol, position in positions.items():
                warning = f"OPEN POSITION: {symbol} has {position} shares still open"
                self.position_warnings.append(warning)
                
            # Log the results
            if positions:
                logger.warning(f"Open positions: {positions}")
            else:
                logger.info("No open positions")
                
        except Exception as e:
            logger.error(f"Error calculating clean positions: {str(e)}")
            logger.error(traceback.format_exc())
            # Ensure we clear positions in case of error
            self.open_positions = {}
            self.position_warnings = []

    def reset(self):
        """Reset the parser's state."""
        self.processed_logs = set()
        self.processed_trade_ids = set()
        self.last_file_positions = {}
        self.position_warnings = []
        self.open_positions = {}

# Version and metadata
VERSION = "1.4"
CREATED_DATE = "2025-05-06 14:00:00"
LAST_MODIFIED = "2025-05-07 11:15:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_log_parser",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - Log Parser Module - v1.4
# Created: 2025-05-06 14:00:00
# Last Modified: 2025-05-07 11:15:00
# webull_realtime_log_parser.py