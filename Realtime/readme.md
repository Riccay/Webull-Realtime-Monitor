# Webull Realtime P&L Monitor

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

A real-time profit and loss monitoring tool for Webull traders that tracks your day trading activity without interfering with the Webull desktop application.

## Features

- **Real-time P&L Tracking**: Monitor your daily trading P&L and performance metrics as they happen
- **Non-invasive Operation**: Works by parsing Webull log files without modifying or interfering with Webull software
- **Advanced Analytics**: Calculate key trading metrics like profit rate, Sharpe ratio, drawdown, and more
- **Trade Pair Matching**: Automatically matches buy and sell executions to calculate accurate P&L
- **Minute-Based Averaging**: Option to use minute-based VWAP pricing for more accurate P&L calculation
- **Position Warnings**: Alerts for unbalanced positions or potential trade matching issues
- **Visual Performance Tracking**: Charts showing P&L performance over time
- **Customizable Interface**: Light/dark mode and custom color themes
- **Trade Tagging & Journaling**: Tag trades and maintain a trading journal (coming soon!)

## Requirements

- Python 3.8 or higher
- Webull Desktop Application (installed and generating log files)
- Required Python packages: `tkinter`, `pandas`, `numpy`, `matplotlib`

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/webull-realtime-pnl.git
   cd webull-realtime-pnl
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the application:
   - The first time you run the application, it will attempt to automatically detect your Webull log folder
   - If auto-detection fails, you can manually set the log folder path in the settings

## Usage

1. Start the application by running:
   ```
   python webull_realtime_pnl.py
   ```

2. Click the "Start" button to begin monitoring
   - The application will scan for new trades in the Webull log files
   - P&L metrics will update in real-time as trades are detected
   
3. View your trading performance:
   - The top panel shows your current day's P&L
   - The metrics panel displays comprehensive trading statistics
   - The chart visualizes your P&L progression throughout the day

## Settings & Configuration

- **Log Folder**: Path to Webull log files (auto-detected or manually set)
- **Scan Interval**: How frequently to check for new trades (in seconds)
- **Auto Start**: Option to automatically start monitoring when application launches
- **Minute-Based Averaging**: Enable/disable minute-based pricing for P&L calculation
- **Dark Mode**: Toggle between light and dark interface themes
- **Custom Colors**: Customize colors for profits, losses, and UI elements

## Project Structure

- `webull_realtime_pnl.py`: Main application module
- `webull_realtime_log_parser.py`: Handles parsing of Webull log files
- `webull_realtime_analytics.py`: P&L and trading metrics calculations
- `webull_realtime_gui.py`: Main GUI interface
- `webull_realtime_gui_components.py`: Additional GUI components
- `webull_realtime_config.py`: Configuration management
- `webull_realtime_common.py`: Common utilities and constants

## Known Limitations

- Currently only supports Windows Webull Desktop application
- Limited to day trading P&L (doesn't track overnight positions)
- P&L calculation precision depends on log file completeness

## Troubleshooting

**No trades being detected:**
- Verify the correct Webull log folder is set
- Ensure Webull is generating log files (make a test trade)
- Check if you have sufficient permissions to read the log files

**Incorrect P&L values:**
- Try enabling the minute-based averaging option
- Check for position warnings that might indicate missing or unpaired trades
- Reset data and allow the application to reprocess all trades

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is not affiliated with, maintained, authorized, endorsed, or sponsored by Webull Financial LLC or any of its affiliates. This is an independent tool that parses locally generated log files.

The tool is provided for informational and educational purposes only. It is not intended to provide trading or investment advice. Always verify P&L data with your official Webull statements.

---

*Webull Realtime P&L Monitor v2.0*  
*Created: 2025-05-06*  
*Last Modified: 2025-05-10*