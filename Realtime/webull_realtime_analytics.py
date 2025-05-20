"""
Webull Realtime P&L Monitor - Analytics Module - v1.3
Created: 2025-05-06 15:30:00
Last Modified: 2025-05-10 16:30:00

This module provides analytics functions for the Webull Realtime P&L Monitor.
It calculates P&L, trading metrics, and statistical analysis.
"""

import os
import pickle
import logging
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta

# Import from common module
from webull_realtime_common import logger, OUTPUT_DIR, truncate_to_minute

class WebullAnalytics:
    """Analytics engine for Webull Realtime P&L Monitor."""
    
    def __init__(self):
        """Initialize the analytics engine."""
        # Trading metrics
        self.day_pnl = 0.0
        self.total_trades = 0
        self.profit_trades = 0
        self.losing_trades = 0
        
        # Basic metrics
        self.profit_rate = 0.0
        self.avg_profit = 0.0
        self.avg_loss = 0.0
        self.profit_factor = 0.0
        
        # Advanced metrics
        self.sharpe_ratio = 0.0
        self.sortino_ratio = 0.0  # New: Sortino ratio
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0  # New: Maximum drawdown percentage
        self.avg_trade_duration = 0.0  # In minutes
        self.expectancy = 0.0  # Average expected profit per trade
        self.consecutive_profits = 0
        self.consecutive_losses = 0
        self.max_consecutive_profits = 0
        self.max_consecutive_losses = 0
        self.largest_profit = 0.0
        self.largest_loss = 0.0
        self.profit_loss_ratio = 0.0  # Avg profit / Avg loss
        self.standard_deviation = 0.0
        
        # Historical data
        self.trade_history = {}  # Dictionary to store historical trades by date
        
        # Trade tags and journal
        self.trade_tags = {}  # Dictionary to store tags for trades by OrderID
        self.journal_entries = {}  # Dictionary to store journal entries by date
        
        # Reference to log parser for position tracking
        self.log_parser = None
        
        # Reference to config
        self.config = None
        
    def set_log_parser(self, log_parser):
        """
        Set the log parser reference for position tracking.
        
        Args:
            log_parser: WebullLogParser instance
        """
        self.log_parser = log_parser
    
    def set_config(self, config):
        """
        Set the config reference.
        
        Args:
            config: WebullConfig instance
        """
        self.config = config
        
    def calculate_pnl(self, trades, trade_pairs=None):
        """
        Calculate P&L from completed trade pairs only.
        This ensures only closed positions affect P&L.
        
        Args:
            trades (list): List of raw trades
            trade_pairs (list, optional): List of matched trade pairs
            
        Returns:
            float: Calculated P&L
        """
        try:
            # Use trade pairs if provided, otherwise try to create them
            if not trade_pairs and self.log_parser:
                trade_pairs = self.log_parser.match_buy_sell_trades(trades)
                
            # If we have trade pairs, calculate P&L from them
            if trade_pairs:
                # Sum P&L from all completed trade pairs
                pnl = sum(pair['PnL'] for pair in trade_pairs)
                
                # Store the P&L value
                self.day_pnl = pnl
                
                logger.info(f"Calculated P&L from {len(trade_pairs)} completed trade pairs: ${pnl:.2f}")
                
                return pnl
                
            # Fallback: If no trade pairs and we have raw trades, calculate from raw trades
            # but only use for UI display, not for actual P&L tracking
            elif trades:
                df = pd.DataFrame(trades)
                
                if df.empty:
                    return 0.0
                    
                # Ensure proper data types
                df['Quantity'] = pd.to_numeric(df['Quantity'])
                df['Price'] = pd.to_numeric(df['Price'])
                
                # Add Commission column if not present
                if 'Commission' not in df.columns:
                    df['Commission'] = 0.0
                else:
                    df['Commission'] = pd.to_numeric(df['Commission'])
                
                # DIRECT P&L CALCULATION: Process all trades
                pnl = 0.0
                
                # Calculate P&L by summing trade values and commissions
                for _, trade in df.iterrows():
                    side = trade['Side'].upper()
                    qty = float(trade['Quantity'])
                    price = float(trade['Price'])
                    commission = float(trade.get('Commission', 0.0))
                    
                    if side == 'BUY':
                        trade_value = -qty * price  # Negative for buys
                    else:  # SELL
                        trade_value = qty * price   # Positive for sells
                    
                    # Subtract commission from value
                    trade_value -= commission
                    
                    # Add to P&L
                    pnl += trade_value
                
                logger.info(f"Calculated P&L from {len(trades)} raw trades: ${pnl:.2f} (fallback method)")
                
                # Important: We don't store this value as self.day_pnl to avoid counting open positions
                # Only complete trade pairs affect the official P&L
                
                # Still return the raw P&L for display purposes
                return pnl
            
            # No trades at all
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating P&L: {str(e)}")
            logger.error(traceback.format_exc())
            return 0.0
    
    def group_trades_by_minute(self, trades):
        """
        Group trades by minute to calculate average prices.
        
        Args:
            trades (list): List of raw trades
            
        Returns:
            dict: Dictionary of trades grouped by minute
        """
        try:
            if not trades:
                return {}
                
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Create minute-truncated DateTime column
            if 'DateTime' not in df.columns:
                if 'Date' in df.columns and 'Time' in df.columns:
                    df['DateTime'] = df['Date'] + ' ' + df['Time']
                else:
                    return {}
            
            # Apply minute truncation
            df['MinuteDateTime'] = df['DateTime'].apply(truncate_to_minute)
            
            # Convert to datetime objects for sorting
            df['DateTimeObj'] = pd.to_datetime(df['DateTime'])
            
            # Sort by datetime
            df = df.sort_values('DateTimeObj')
            
            # Group trades by symbol and minute
            grouped_trades = {}
            
            for symbol in df['Symbol'].unique():
                symbol_trades = df[df['Symbol'] == symbol]
                
                for minute, minute_df in symbol_trades.groupby('MinuteDateTime'):
                    # Calculate average price for buys and sells within this minute
                    buys = minute_df[minute_df['Side'].str.upper() == 'BUY']
                    sells = minute_df[minute_df['Side'].str.upper() == 'SELL']
                    
                    # Calculate volume-weighted average prices
                    if not buys.empty:
                        avg_buy_price = (buys['Price'] * buys['Quantity']).sum() / buys['Quantity'].sum()
                    else:
                        avg_buy_price = None
                        
                    if not sells.empty:
                        avg_sell_price = (sells['Price'] * sells['Quantity']).sum() / sells['Quantity'].sum()
                    else:
                        avg_sell_price = None
                    
                    # Create a key for this symbol and minute
                    key = f"{symbol}_{minute}"
                    
                    # Store the average prices and raw trades
                    grouped_trades[key] = {
                        'symbol': symbol,
                        'minute': minute,
                        'avg_buy_price': avg_buy_price,
                        'avg_sell_price': avg_sell_price,
                        'buy_trades': buys.to_dict('records') if not buys.empty else [],
                        'sell_trades': sells.to_dict('records') if not sells.empty else [],
                        'total_buy_qty': buys['Quantity'].sum() if not buys.empty else 0,
                        'total_sell_qty': sells['Quantity'].sum() if not sells.empty else 0
                    }
            
            return grouped_trades
            
        except Exception as e:
            logger.error(f"Error grouping trades by minute: {str(e)}")
            logger.error(traceback.format_exc())
            return {}
    
    def calculate_advanced_metrics(self, trade_pairs):
        """
        Calculate advanced trading metrics from completed trade pairs.
        
        Args:
            trade_pairs (list): List of completed trade pairs
            
        Returns:
            dict: Dictionary of calculated metrics
        """
        try:
            if not trade_pairs:
                self.reset_metrics()
                return self.get_metrics_dict()
                
            # Use the minute-based average pricing if enabled in config
            if self.config and self.config.minute_based_avg:
                # Implementation of minute-based price averaging for better P&L calculation
                # This will replace or update the trade_pairs with minute-based average pricing
                trade_pairs = self.apply_minute_based_pricing(trade_pairs)
                
            # Create DataFrame from trade pairs
            df = pd.DataFrame(trade_pairs)
            
            # Basic metrics
            profit_trades = df[df['PnL'] > 0]
            loss_trades = df[df['PnL'] < 0]
            
            num_profit_trades = len(profit_trades)
            num_loss_trades = len(loss_trades)
            total_trades = len(df)
            
            self.total_trades = total_trades
            self.profit_trades = num_profit_trades
            self.losing_trades = num_loss_trades
            
            self.profit_rate = (num_profit_trades / total_trades) * 100 if total_trades > 0 else 0
            
            self.avg_profit = profit_trades['PnL'].mean() if not profit_trades.empty else 0
            self.avg_loss = loss_trades['PnL'].mean() if not loss_trades.empty else 0
            
            total_profit = profit_trades['PnL'].sum() if not profit_trades.empty else 0
            total_loss = abs(loss_trades['PnL'].sum()) if not loss_trades.empty else 0
            
            # Calculate day P&L and store
            self.day_pnl = total_profit - total_loss
            
            # Calculate profit factor
            self.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
            
            # Calculate returns per trade
            returns = df['PnLPercent'] / 100  # Convert percent to decimal
            
            # Calculate Sharpe Ratio (simplified - using 0 as risk-free rate)
            self.sharpe_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
            
            # Calculate Sortino Ratio (using only negative returns to calculate downside deviation)
            negative_returns = returns[returns < 0]
            downside_deviation = negative_returns.std() if not negative_returns.empty and len(negative_returns) > 1 else 0.0001
            self.sortino_ratio = returns.mean() / downside_deviation if downside_deviation > 0 else 0
            
            # Calculate Maximum Drawdown
            # First, create a cumulative P&L series
            df = df.sort_values('SellTime')
            df['CumulativePnL'] = df['PnL'].cumsum()
            
            # Calculate running maximum
            df['RunningMax'] = df['CumulativePnL'].cummax()
            
            # Calculate drawdown
            df['Drawdown'] = df['RunningMax'] - df['CumulativePnL']
            
            # Get maximum drawdown
            self.max_drawdown = df['Drawdown'].max()
            
            # Calculate maximum drawdown percentage if we have a running max
            if not df.empty and df['RunningMax'].max() > 0:
                # Formula: (Peak - Trough) / Peak
                peak_idx = df['RunningMax'].idxmax()
                peak_value = df.loc[peak_idx, 'RunningMax']
                
                # Find the largest drawdown as a percentage of the peak
                df['DrawdownPct'] = df['Drawdown'] / df['RunningMax'] * 100
                self.max_drawdown_pct = df['DrawdownPct'].max()
            else:
                self.max_drawdown_pct = 0.0
            
            # Average trade duration in minutes
            self.avg_trade_duration = df['DurationMinutes'].mean()
            
            # Expectancy
            self.expectancy = (self.avg_profit * self.profit_rate/100) + (self.avg_loss * (1 - self.profit_rate/100))
            
            # Consecutive profits/losses tracking
            if not df.empty:
                results = df.sort_values('SellTime')['Result'].tolist()
                
                current_streak = 1
                max_profit_streak = 0
                max_loss_streak = 0
                
                if results[0] == 'Profit':
                    current_profit_streak = 1
                    current_loss_streak = 0
                else:
                    current_profit_streak = 0
                    current_loss_streak = 1
                
                for i in range(1, len(results)):
                    if results[i] == results[i-1]:
                        current_streak += 1
                    else:
                        current_streak = 1
                    
                    if results[i] == 'Profit':
                        current_profit_streak = current_streak
                        current_loss_streak = 0
                        max_profit_streak = max(max_profit_streak, current_profit_streak)
                    else:
                        current_loss_streak = current_streak
                        current_profit_streak = 0
                        max_loss_streak = max(max_loss_streak, current_loss_streak)
                
                self.consecutive_profits = current_profit_streak
                self.consecutive_losses = current_loss_streak
                self.max_consecutive_profits = max_profit_streak
                self.max_consecutive_losses = max_loss_streak
            else:
                self.consecutive_profits = 0
                self.consecutive_losses = 0
                self.max_consecutive_profits = 0
                self.max_consecutive_losses = 0
            
            # Largest profit and loss
            self.largest_profit = profit_trades['PnL'].max() if not profit_trades.empty else 0
            self.largest_loss = loss_trades['PnL'].min() if not loss_trades.empty else 0
            
            # Profit to loss ratio (R-ratio)
            self.profit_loss_ratio = abs(self.avg_profit / self.avg_loss) if self.avg_loss != 0 else float('inf') if self.avg_profit > 0 else 0
            
            # Standard deviation of P&L
            self.standard_deviation = df['PnL'].std()
            
            # Return metrics as a dictionary
            return self.get_metrics_dict()
        
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return empty metrics
            self.reset_metrics()
            return self.get_metrics_dict()
    
    def apply_minute_based_pricing(self, trade_pairs):
        """
        Apply minute-based average pricing to trade pairs.
        
        Args:
            trade_pairs (list): List of trade pairs
            
        Returns:
            list: Updated trade pairs with minute-based average pricing
        """
        try:
            if not trade_pairs:
                return []
                
            # Convert to DataFrame
            df = pd.DataFrame(trade_pairs)
            
            if df.empty:
                return trade_pairs
                
            # Create minute-truncated DateTime columns for buy and sell times
            df['BuyMinute'] = df['BuyTime'].apply(truncate_to_minute)
            df['SellMinute'] = df['SellTime'].apply(truncate_to_minute)
            
            # Group by symbol and minute for buy and sell separately
            buy_groups = {}
            sell_groups = {}
            
            for symbol in df['Symbol'].unique():
                symbol_df = df[df['Symbol'] == symbol]
                
                # Group buy prices by minute
                for buy_minute, buy_df in symbol_df.groupby('BuyMinute'):
                    # Calculate volume-weighted average buy price
                    avg_buy_price = (buy_df['BuyPrice'] * buy_df['Quantity']).sum() / buy_df['Quantity'].sum()
                    buy_groups[(symbol, buy_minute)] = avg_buy_price
                
                # Group sell prices by minute
                for sell_minute, sell_df in symbol_df.groupby('SellMinute'):
                    # Calculate volume-weighted average sell price
                    avg_sell_price = (sell_df['SellPrice'] * sell_df['Quantity']).sum() / sell_df['Quantity'].sum()
                    sell_groups[(symbol, sell_minute)] = avg_sell_price
            
            # Apply average prices to trade pairs
            for i, pair in enumerate(trade_pairs):
                symbol = pair['Symbol']
                buy_minute = truncate_to_minute(pair['BuyTime'])
                sell_minute = truncate_to_minute(pair['SellTime'])
                
                # Get average prices if available
                if (symbol, buy_minute) in buy_groups:
                    avg_buy_price = buy_groups[(symbol, buy_minute)]
                    trade_pairs[i]['BuyPrice'] = avg_buy_price
                    trade_pairs[i]['BuyCost'] = avg_buy_price * pair['Quantity']
                    
                if (symbol, sell_minute) in sell_groups:
                    avg_sell_price = sell_groups[(symbol, sell_minute)]
                    trade_pairs[i]['SellPrice'] = avg_sell_price
                    trade_pairs[i]['SellProceeds'] = avg_sell_price * pair['Quantity']
                
                # Recalculate P&L
                buy_cost = trade_pairs[i]['BuyCost']
                sell_proceeds = trade_pairs[i]['SellProceeds']
                buy_commission = trade_pairs[i].get('BuyCommission', 0)
                sell_commission = trade_pairs[i].get('SellCommission', 0)
                
                total_cost = buy_cost + buy_commission
                total_proceeds = sell_proceeds - sell_commission
                
                # Update P&L values
                trade_pairs[i]['PnL'] = total_proceeds - total_cost
                trade_pairs[i]['PnLPercent'] = (trade_pairs[i]['PnL'] / total_cost) * 100 if total_cost > 0 else 0
                trade_pairs[i]['Result'] = 'Profit' if trade_pairs[i]['PnL'] > 0 else 'Loss'
                trade_pairs[i]['TotalCost'] = total_cost
            
            return trade_pairs
                
        except Exception as e:
            logger.error(f"Error applying minute-based pricing: {str(e)}")
            logger.error(traceback.format_exc())
            return trade_pairs
    
    def reset_metrics(self):
        """Reset all metrics to default values."""
        self.day_pnl = 0.0
        self.total_trades = 0
        self.profit_trades = 0
        self.losing_trades = 0
        
        self.profit_rate = 0.0
        self.avg_profit = 0.0
        self.avg_loss = 0.0
        self.profit_factor = 0.0
        self.sharpe_ratio = 0.0
        self.sortino_ratio = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.avg_trade_duration = 0.0
        self.expectancy = 0.0
        self.consecutive_profits = 0
        self.consecutive_losses = 0
        self.max_consecutive_profits = 0
        self.max_consecutive_losses = 0
        self.largest_profit = 0.0
        self.largest_loss = 0.0
        self.profit_loss_ratio = 0.0
        self.standard_deviation = 0.0
        
    def get_metrics_dict(self):
        """
        Get all metrics as a dictionary.
        
        Returns:
            dict: Dictionary of all metrics
        """
        return {
            'day_pnl': self.day_pnl,
            'total_trades': self.total_trades,
            'profit_trades': self.profit_trades,
            'losing_trades': self.losing_trades,
            'profit_rate': self.profit_rate,
            'avg_profit': self.avg_profit,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'avg_trade_duration': self.avg_trade_duration,
            'expectancy': self.expectancy,
            'consecutive_profits': self.consecutive_profits,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_profits': self.max_consecutive_profits,
            'max_consecutive_losses': self.max_consecutive_losses,
            'largest_profit': self.largest_profit,
            'largest_loss': self.largest_loss,
            'profit_loss_ratio': self.profit_loss_ratio,
            'standard_deviation': self.standard_deviation
        }
    
    # Trade tagging functionality
    def add_trade_tag(self, order_id, tag):
        """
        Add a tag to a trade.
        
        Args:
            order_id (str): Order ID of the trade
            tag (str): Tag to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if order_id not in self.trade_tags:
                self.trade_tags[order_id] = []
                
            # Add tag if not already present
            if tag not in self.trade_tags[order_id]:
                self.trade_tags[order_id].append(tag)
                logger.info(f"Added tag '{tag}' to trade {order_id}")
                
                # Save tags
                self.save_trade_tags()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding trade tag: {str(e)}")
            return False
            
    def remove_trade_tag(self, order_id, tag):
        """
        Remove a tag from a trade.
        
        Args:
            order_id (str): Order ID of the trade
            tag (str): Tag to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if order_id in self.trade_tags and tag in self.trade_tags[order_id]:
                self.trade_tags[order_id].remove(tag)
                logger.info(f"Removed tag '{tag}' from trade {order_id}")
                
                # Clean up empty tag lists
                if not self.trade_tags[order_id]:
                    del self.trade_tags[order_id]
                    
                # Save tags
                self.save_trade_tags()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing trade tag: {str(e)}")
            return False
            
    def get_trade_tags(self, order_id=None):
        """
        Get tags for a specific trade or all tags.
        
        Args:
            order_id (str, optional): Order ID to get tags for
            
        Returns:
            list or dict: Tags for the specified trade or all tags
        """
        if order_id:
            return self.trade_tags.get(order_id, [])
        return self.trade_tags
        
    def save_trade_tags(self):
        """
        Save trade tags to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            tags_file = os.path.join(OUTPUT_DIR, "trade_tags.pkl")
            
            with open(tags_file, 'wb') as f:
                pickle.dump(self.trade_tags, f)
                
            logger.info(f"Saved {len(self.trade_tags)} trade tags")
            return True
        except Exception as e:
            logger.error(f"Error saving trade tags: {str(e)}")
            return False
            
    def load_trade_tags(self):
        """
        Load trade tags from file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            tags_file = os.path.join(OUTPUT_DIR, "trade_tags.pkl")
            
            if os.path.exists(tags_file):
                with open(tags_file, 'rb') as f:
                    self.trade_tags = pickle.load(f)
                    
                logger.info(f"Loaded {len(self.trade_tags)} trade tags")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading trade tags: {str(e)}")
            return False
    
    # Journal entry functionality
    def add_journal_entry(self, date_str, entry):
        """
        Add a journal entry for a specific date.
        
        Args:
            date_str (str): Date string in format YYYY-MM-DD
            entry (str): Journal entry text
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use today if no date provided
            if not date_str:
                date_str = datetime.now().strftime("%Y-%m-%d")
                
            # Add entry with timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            if date_str not in self.journal_entries:
                self.journal_entries[date_str] = []
                
            self.journal_entries[date_str].append({
                'timestamp': timestamp,
                'entry': entry
            })
            
            logger.info(f"Added journal entry for {date_str}")
            
            # Save journal
            self.save_journal()
            return True
        except Exception as e:
            logger.error(f"Error adding journal entry: {str(e)}")
            return False
            
    def get_journal_entries(self, date_str=None):
        """
        Get journal entries for a specific date or all entries.
        
        Args:
            date_str (str, optional): Date string in format YYYY-MM-DD
            
        Returns:
            list or dict: Entries for the specified date or all entries
        """
        if date_str:
            return self.journal_entries.get(date_str, [])
        return self.journal_entries
        
    def save_journal(self):
        """
        Save journal entries to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            journal_file = os.path.join(OUTPUT_DIR, "trade_journal.pkl")
            
            with open(journal_file, 'wb') as f:
                pickle.dump(self.journal_entries, f)
                
            logger.info(f"Saved journal with {len(self.journal_entries)} days of entries")
            return True
        except Exception as e:
            logger.error(f"Error saving journal: {str(e)}")
            return False
            
    def load_journal(self):
        """
        Load journal entries from file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            journal_file = os.path.join(OUTPUT_DIR, "trade_journal.pkl")
            
            if os.path.exists(journal_file):
                with open(journal_file, 'rb') as f:
                    self.journal_entries = pickle.load(f)
                    
                logger.info(f"Loaded journal with {len(self.journal_entries)} days of entries")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading journal: {str(e)}")
            return False
            
    def load_historical_trades(self):
        """
        Load historical trades from saved files.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            history_file = os.path.join(OUTPUT_DIR, "trade_history.pkl")
            
            if os.path.exists(history_file):
                with open(history_file, 'rb') as f:
                    self.trade_history = pickle.load(f)
                    
                logger.info(f"Loaded trade history with {len(self.trade_history)} trading days")
                
            # Load trade tags and journal
            self.load_trade_tags()
            self.load_journal()
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading trade history: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    def save_historical_trades(self, today_trades=None):
        """
        Save trades history to file for later analysis.
        
        Args:
            today_trades (list, optional): Today's trades to add to history
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add today's trades to history if provided and not empty
            if today_trades:
                today_str = datetime.now().strftime("%Y-%m-%d")
                self.trade_history[today_str] = today_trades
            
            # Save to file
            history_file = os.path.join(OUTPUT_DIR, "trade_history.pkl")
            
            with open(history_file, 'wb') as f:
                pickle.dump(self.trade_history, f)
                
            logger.info(f"Saved trade history with {len(self.trade_history)} trading days")
            
            # Save trade tags and journal
            self.save_trade_tags()
            self.save_journal()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving trade history: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_daily_summary(self):
        """
        Get a summary of trading performance for past days.
        
        Returns:
            dict: Dictionary with daily performance summaries
        """
        summary = {
            'dates': [],
            'pnl': [],
            'trades': [],
            'profit_rate': [],
            'profit_factor': []
        }
        
        try:
            if not self.trade_history:
                return summary
                
            # Process each day in history
            for date_str, trades in sorted(self.trade_history.items()):
                # Skip empty days
                if not trades:
                    continue
                    
                # Create DataFrame for this day's trades
                df = pd.DataFrame(trades)
                
                # Skip if no trades
                if df.empty:
                    continue
                    
                # Calculate day's P&L
                day_pnl = 0.0
                total_trades = 0
                profit_trades = 0
                
                # Check if this has trade pairs with PnL already calculated
                if 'PnL' in df.columns:
                    # This is already trade pairs data
                    day_pnl = df['PnL'].sum()
                    total_trades = len(df)
                    profit_trades = len(df[df['PnL'] > 0])
                else:
                    # Calculate from raw trades
                    for _, trade in df.iterrows():
                        side = trade['Side'].upper()
                        qty = float(trade['Quantity'])
                        price = float(trade['Price'])
                        commission = float(trade.get('Commission', 0.0))
                        
                        if side == 'BUY':
                            trade_value = -qty * price  # Negative for buys
                        else:  # SELL
                            trade_value = qty * price   # Positive for sells
                        
                        # Subtract commission from value
                        trade_value -= commission
                        
                        # Add to P&L
                        day_pnl += trade_value
                
                # Calculate profit rate and factor if we have trade pairs
                profit_rate = 0.0
                profit_factor = 0.0
                
                if 'PnL' in df.columns:
                    profit_trades = len(df[df['PnL'] > 0])
                    loss_trades = len(df[df['PnL'] < 0])
                    
                    profit_rate = (profit_trades / total_trades) * 100 if total_trades > 0 else 0
                    
                    total_profit = df[df['PnL'] > 0]['PnL'].sum() if not df[df['PnL'] > 0].empty else 0
                    total_loss = abs(df[df['PnL'] < 0]['PnL'].sum()) if not df[df['PnL'] < 0].empty else 0
                    
                    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
                
                # Add to summary
                summary['dates'].append(date_str)
                summary['pnl'].append(day_pnl)
                summary['trades'].append(total_trades)
                summary['profit_rate'].append(profit_rate)
                summary['profit_factor'].append(profit_factor if profit_factor != float('inf') else 999.99)
                
            return summary
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {str(e)}")
            logger.error(traceback.format_exc())
            return summary
    
    def get_trading_statistics(self):
        """
        Calculate overall trading statistics across all historical data.
        
        Returns:
            dict: Dictionary with overall trading statistics
        """
        stats = {
            'total_days': 0,
            'profitable_days': 0,
            'losing_days': 0,
            'total_pnl': 0.0,
            'total_trades': 0,
            'avg_trades_per_day': 0.0,
            'avg_pnl_per_day': 0.0,
            'avg_profit_rate': 0.0,
            'avg_profit_factor': 0.0,
            'best_day_pnl': 0.0,
            'worst_day_pnl': 0.0,
            'best_day_date': '',
            'worst_day_date': ''
        }
        
        try:
            # Get daily summary
            summary = self.get_daily_summary()
            
            if not summary['dates']:
                return stats
                
            # Basic statistics
            stats['total_days'] = len(summary['dates'])
            stats['profitable_days'] = sum(1 for pnl in summary['pnl'] if pnl > 0)
            stats['losing_days'] = sum(1 for pnl in summary['pnl'] if pnl < 0)
            stats['total_pnl'] = sum(summary['pnl'])
            stats['total_trades'] = sum(summary['trades'])
            stats['avg_trades_per_day'] = stats['total_trades'] / stats['total_days'] if stats['total_days'] > 0 else 0
            stats['avg_pnl_per_day'] = stats['total_pnl'] / stats['total_days'] if stats['total_days'] > 0 else 0
            
            # Filter out infinite profit factors
            valid_profit_factors = [pf for pf in summary['profit_factor'] if pf != float('inf') and pf != 999.99]
            stats['avg_profit_factor'] = sum(valid_profit_factors) / len(valid_profit_factors) if valid_profit_factors else 0
            
            # Average profit rate
            stats['avg_profit_rate'] = sum(summary['profit_rate']) / len(summary['profit_rate']) if summary['profit_rate'] else 0
            
            # Best and worst days
            if summary['pnl']:
                best_index = summary['pnl'].index(max(summary['pnl']))
                worst_index = summary['pnl'].index(min(summary['pnl']))
                
                stats['best_day_pnl'] = summary['pnl'][best_index]
                stats['worst_day_pnl'] = summary['pnl'][worst_index]
                stats['best_day_date'] = summary['dates'][best_index]
                stats['worst_day_date'] = summary['dates'][worst_index]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating trading statistics: {str(e)}")
            logger.error(traceback.format_exc())
            return stats

# Version and metadata
VERSION = "1.3"
CREATED_DATE = "2025-05-06 15:30:00"
LAST_MODIFIED = "2025-05-10 16:30:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_analytics",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - Analytics Module - v1.3
# Created: 2025-05-06 15:30:00
# Last Modified: 2025-05-10 16:30:00
# webull_realtime_analytics.py