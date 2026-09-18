<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Wolf%20Rush%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Bonus%20%7C%20Mining%20Slots%20%7C%20Auto%20Tasks%20%7C%20Reward%20Ads%20%7C%20Multi-Account&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Daily+Bonus+%7C+Channel+Gate+Required;Auto+Mining+Slots+%7C+Ad-Powered+Per+Slot;Auto+Slot+Claim+%7C+Skip+Ready+Cooldown;Auto+Tasks+%7C+Main+and+Other+Task+Groups;Auto+Reward+Ads+%7C+Per+Card+Cooldown+Handling;Promo+Code+Support+%7C+Optional+Wolf+Reward;Proxy+Support+%7C+One+Proxy+Per+Account;Multi-Account+%7C+Sequential+Processing+Per+Cycle"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Wolf%20Rush%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Wolf Rush Miniapp Bot</b> is a full automation bot for the Wolf Rush Telegram Miniapp.<br/>
  It handles the complete daily cycle: authenticating each account, checking the channel gate and claiming the daily bonus when the gate is passed, redeeming a promo code when one is set, working through all mining slots by watching the required ads per slot and claiming ready slots, completing all pending tasks from the main and other groups, processing all available reward ad cards up to their daily limits, and submitting a withdrawal request when a wallet is set and the minimum is met, all running across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Wolfrush-Miniapp.git
cd Wolfrush-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line. To include a payout wallet address for withdrawal requests, append a pipe character followed by the wallet address on the same line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456|YourWalletAddressHere
```

The wallet address after the pipe is optional. If omitted, the withdrawal request step is skipped for that account.

> `initData` can be obtained from the browser DevTools when opening Wolf Rush on Telegram Web.

### 2. Proxy (proxy.txt) - Optional

Fill `proxy.txt` with proxies, one per line. Proxies are assigned to accounts by index (first proxy to first account, second proxy to second account, and so on). If the number of proxies is fewer than the number of accounts, proxies wrap around cyclically. If `proxy.txt` is missing or empty, the bot runs without a proxy.

```
http://user:pass@ip:port
http://user:pass@ip:port
```

Supported formats: `http://user:pass@host:port` or `host:port:user:pass`

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, the bot falls back to a default of `3600` seconds.

```json
{
  "settings": {
    "sleep_seconds": 3600
  }
}
```

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Login
The bot authenticates each account by reading the dashboard using the `initData` string. The username and current wolf balance are logged on successful sign-in. If sign-in fails, the account is skipped for that cycle.

### Channel Gate Check
The bot checks whether the account has passed the channel join requirement. If all channels are confirmed, the daily bonus is unlocked and claimed. If any channel is still missing, the first missing channel name is logged and the daily bonus step is skipped for that account.

### Auto Daily Bonus
If the channel gate passes, the bot sends a daily bonus request and logs the wolf reward on success. If the bonus was already claimed today, that is logged and the step is skipped.

### Promo Code
If a promo code is set in the bot source, the bot sends a redeem request for each account and logs the wolf reward on success. If the code is not accepted or has already been used, that is logged and the step is skipped.

### Auto Mining Slots
The bot fetches the mining slot list and checks the daily claim limit against claims already made today. For each slot, the bot reads whether it is ready to claim, how many ads have been watched, and how many are required. If a slot is ready, a claim request is sent immediately and the wolf reward is logged. If a slot still needs ads, the bot watches them one by one until all required ads are counted, after which the slot enters its mining cooldown. Slots that have already started mining and are still within their cooldown window are logged with the remaining wait time and skipped.

### Auto Tasks
The bot fetches tasks from both the main and other task groups and processes all that are not yet marked done. A claim request is sent for each pending task and the wolf reward is logged on success. Tasks that are refused by the server have their reason logged and are skipped.

### Auto Reward Ads
The bot fetches the reward ad card list and filters for cards that still have remaining views. For each active card, claim requests are sent one by one until the card limit is reached or the server refuses the next claim. Between each claim, the per-card cooldown returned by the server is respected. Each credited ad view and its wolf reward are logged individually.

### Withdraw Gate Pass
After all earning actions complete, the bot fetches the withdraw gate pass progress and logs how many steps have been completed out of the total required before withdrawal is unlocked.

### Auto Withdrawal Request
If a wallet address is provided in `data.txt`, the bot checks the wallet config from the server to confirm withdrawals are enabled and reads the minimum and maximum thresholds. If the wolf balance meets the minimum, a withdrawal request is submitted using the first available method and the result is logged. If the balance has not reached the minimum or withdrawals are disabled by the server, the step is logged and skipped.

### Proxy Support
Each account can be assigned its own proxy via `proxy.txt`. If a proxy is configured for the current account, it is shown in masked form before processing begins. Proxy assignment uses a round-robin fallback if there are fewer proxies than accounts. Both `http://user:pass@host:port` and `host:port:user:pass` formats are supported.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Username and wolf balance are logged at the start of each account. Final balance in wolf and its USDT equivalent are logged after all actions complete. A blank line separates each account output in the terminal for readability.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown in the terminal until the next cycle starts, then re-shows the banner before beginning again.

---

## File Structure

```text
Wolfrush-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData and optional wallet, one per line
├── proxy.txt       # Proxies, one per line (optional)
├── LICENSE         # License file
└── utils/
    ├── banner.py   # Banner display on startup
    └── __init__.py
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>