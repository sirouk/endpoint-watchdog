# Endpoint Watchdog

This Python script monitors changes in JSON responses from a specified endpoint and sends notifications via Discord webhook when changes are detected. It's designed to run continuously, checking for updates at regular intervals.

## Features

- Monitors JSON responses from any endpoint
- Sends notifications through Discord webhooks
- Generates and displays readable diffs of detected changes
- Caches responses to efficiently detect differences
- Auto-updates from the GitHub repository (optional)
- Easy setup with interactive prompts for configuration
- Can be run as a background service using PM2 with log rotation

## Requirements

- **Python** 3.6+
- **Node.js** and npm (for PM2 installation)

## Installation

Install system packages:

```bash
sudo apt update

# python3
sudo apt install -y python3 python3-pip python3-venv

# npm and additional tools
sudo apt install jq npm -y

# pm2 and enable startup on reboot (careful, this restarts pm2 processes)
npm install pm2@latest -g && pm2 update && pm2 save --force && pm2 startup && pm2 save
```

Clone this repository:

```bash
cd $HOME
git clone https://github.com/sirouk/endpoint-watchdog.git
cd endpoint-watchdog
```

Install the required Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Running manually

Run the script:

```bash
cd $HOME/endpoint-watchdog
source .venv/bin/activate
python3 endpoint_watchdog.py
```

On the first run, you will be prompted to enter your endpoint URL, watch interval, Discord webhook URL, and Discord mention code. The script will validate these inputs and save them to a `.env` file for future use.

### Running as a PM2 service

Start the PM2 service:

```bash
pm2 start "python3 endpoint_watchdog.py custom-name" --name "custom-name-watchdog"
pm2 save --force
```

Set up PM2 Logrotate:

```bash
# Install pm2-logrotate module
pm2 install pm2-logrotate
# Set maximum size of logs to 50M before rotation
pm2 set pm2-logrotate:max_size 50M
# Retain 10 rotated log files
pm2 set pm2-logrotate:retain 10
# Enable compression of rotated logs
pm2 set pm2-logrotate:compress true
# Set rotation interval to every 6 hours
pm2 set pm2-logrotate:rotateInterval '00 */6 * * *'
```

To view logs:

```bash
pm2 logs custom-name-watchdog
```

To stop the service:

```bash
pm2 stop custom-name-watchdog
```

To restart the service:

```bash
pm2 restart custom-name-watchdog
```

## Configuration

The script uses the following variables that you can configure in the `.env` file or during the initial setup:

- `ENDPOINT_URL`: The URL of the JSON endpoint to monitor
- `WATCH_INTERVAL`: The interval in minutes between each check
- `DISCORD_WEBHOOK_URL`: The Discord webhook URL to send notifications
- `DISCORD_MENTION_CODE`: The Discord group to tag for the change notifications. You can get this by putting a \ in front of a mention and sending a message in discord GUI client

Additional constants in the code:

- `CACHE_FILE`: Filename for caching responses
- `auto_update_enabled`: Set to `True` to enable auto-updates from the GitHub repository
- `UPDATE_INTERVAL_MULTIPLIER`: Multiplier for how often updates are checked relative to the watch interval
- `DISCORD_MAX_LENGTH`: Maximum size of a message to send to Discord before truncation
- `DPASTE_MAX_LENGTH`: Maximum size of the diff to to include in a dpaste link before truncation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This script is not officially associated with any endpoint provider. Use at your own risk.
