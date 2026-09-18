import os
import sys
import json
import time
import signal
import asyncio
import aiohttp

from urllib.parse import parse_qs, unquote

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Wolf Rush Miniapp"
BASE_URL = "https://wolf-rush-earn.lovable.app"
REF_CODE = "6004380466"

PAYOUT_WALLET = ""
PROMO_CODE = ""

CALL_ATTEMPTS = 3
CALL_RETRY_SECONDS = 4
ROUND_PAUSE_SECONDS = 1
IDLE_PAUSE_SECONDS = 1

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
)

FN_PROFILE = "356e08e4606b387c62bf2144a50531f9b42e037705e318eff57895a9e5b7b3f2"
FN_CHANNELS = "89ec6b1a593746569bd24ab2448cb40ca78edd24b2c74e794fd75e5d6b5f5901"
FN_DAILY_BONUS = "e1bfbc5af3a0aa8d9eb2be1682b2e9de03d0e8d736c809357ab26ab0f3831c64"
FN_PROMO = "27ad746716aec12da0f9395d8313080b4fb6717210254957641503a967d57756"
FN_ADS_STATUS = "b5c451b99881e0f0941e834ba48bd38bb77f8308b0f3dc05f53d2accd8b14790"
FN_AD_CLAIM = "8a870ea9ebd30dc096c0f8f04f8cfdcae526e7efc008f44693d47a9465554511"
FN_MINE_STATUS = "34ab5246de7b4c512d978fab74abb1eaceae49bc5c0e4d43f68f629e650ee350"
FN_MINE_AD = "5572274f3fe9809ed72d28c2e127c4c4980b9899c3ffe18f33be17bc42fefdfd"
FN_MINE_CLAIM = "5c9bf7136aa2ad055692ff1c019fd83d6ab3a85532496c89ead2ed0255175402"
FN_TASKS = "114189333ba445a53537785a6e9cf24e442f165407dac8a863a44fe524d613a8"
FN_TASK_CLAIM = "871b5531ea071874a9cebfa5d4f46bfee30148d4902603e254a701b72e23dd5f"
FN_REFERRAL = "a073a0f4b918f6f9065085dd02a344cc3216897e0a71a554fcccc07ad164f4b1"
FN_WALLET = "f02ff708078ecdaf25e06894a8399bca27cd516e3617cf6ff1208cbb77bc12c8"
FN_GATE_PASS = "fd1ae7e33bb8c7b59dceedbadb76e4d5efd0da1c7ddf471b52f892294280042e"
FN_WITHDRAW = "fee11aaeb5ab4f917e77d418308f19904a6ed0bc43ddabe5b8c2ee0ef10e80b3"

CONST_MAP = {0: None, 1: None, 2: True, 3: False}


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def unit_word(value, singular, plural):
    try:
        return singular if int(float(value)) == 1 else plural
    except Exception:
        return plural


def format_amount(value):
    try:
        number = round(float(value), 6)
    except Exception:
        return str(value)
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def format_int(value):
    try:
        return str(int(float(value)))
    except Exception:
        return "0"


def number_of(mapping, key, fallback=0.0):
    if not isinstance(mapping, dict):
        return fallback
    try:
        return float(mapping.get(key) or 0)
    except Exception:
        return fallback


def text_of(mapping, key, fallback=""):
    if not isinstance(mapping, dict):
        return fallback
    value = mapping.get(key)
    return fallback if value is None else str(value)


def reason_text(error, fallback):
    if isinstance(error, dict):
        text = error.get("__error__") or error.get("message") or ""
    elif error is None:
        text = ""
    else:
        text = str(error)
    return shorten(text, fallback, 22)


def display_name(dashboard, account):
    user = dashboard.get("user") if isinstance(dashboard, dict) else {}
    for value in (
        user.get("first_name") if isinstance(user, dict) else None,
        account.get("firstName"),
        user.get("username") if isinstance(user, dict) else None,
        account.get("username"),
    ):
        name = clean_text(value, "")
        if name:
            return name
    return "Unknown"


def encode_node(value):
    counter = [0]

    def walk(item):
        if item is True:
            return {"t": 2, "s": 2}
        if item is False:
            return {"t": 2, "s": 3}
        if item is None:
            return {"t": 2, "s": 0}
        if isinstance(item, (int, float)):
            return {"t": 0, "s": item}
        if isinstance(item, str):
            return {"t": 1, "s": item}
        if isinstance(item, dict):
            counter[0] += 1
            return {
                "t": 10,
                "i": counter[0],
                "p": {"k": list(item.keys()), "v": [walk(x) for x in item.values()]},
                "o": 0,
            }
        if isinstance(item, (list, tuple)):
            counter[0] += 1
            return {"t": 9, "i": counter[0], "a": [walk(x) for x in item], "o": 0}
        return {"t": 1, "s": str(item)}

    return walk(value)


def decode_node(node):
    if not isinstance(node, dict):
        return node
    kind = node.get("t")
    if kind in (0, 1):
        return node.get("s")
    if kind == 2:
        return CONST_MAP.get(node.get("s"))
    if kind == 9:
        return [decode_node(item) for item in node.get("a", [])]
    if kind in (10, 11):
        payload = node.get("p") or {}
        keys = payload.get("k") or []
        values = payload.get("v") or []
        return {key: decode_node(item) for key, item in zip(keys, values)}
    if kind == 25:
        raw = node.get("s")
        if isinstance(raw, dict) and isinstance(raw.get("message"), dict):
            return {"__error__": decode_node(raw.get("message"))}
        return {"__error__": str(raw)}
    return None


def unwrap(node):
    data = decode_node(node)
    if isinstance(data, dict) and ("result" in data or "error" in data):
        error = data.get("error")
        if isinstance(error, dict):
            error = error.get("__error__", error)
        return data.get("result"), error
    return data, None


def tsr_body(payload):
    return json.dumps(
        {"t": encode_node({"data": payload}), "f": 63, "m": []},
        separators=(",", ":"),
    )


def build_headers(init_data):
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": BASE_URL,
        "referer": BASE_URL + "/",
        "user-agent": USER_AGENT,
        "x-tsr-serverfn": "true",
        "x-telegram-init-data": init_data,
    }


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def countdown(seconds, label):
    total = int(seconds)
    if total < 1:
        return
    line = ""
    for remaining in range(total, 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        line = f"{label} {hours:02d}:{minutes:02d}:{rest:02d}"
        print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * (len(line) + 6) + "\r", end="", flush=True)


def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            return json.load(handle)
    except Exception:
        return defaults


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red("File data.txt was not found in this folder")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines


def parse_init_data(line):
    value = line.strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0].split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
        "lastName": str(profile.get("last_name") or ""),
    }


def busy_error(status, payload):
    if status in (500, 502, 503, 504):
        return True
    if isinstance(payload, dict):
        message = str(payload.get("message") or "")
    else:
        message = str(payload or "")
    message = message.lower()
    return "busy" in message or "timeout" in message


async def post_fn(session, fn_id, payload, headers, proxy):
    url = f"{BASE_URL}/_serverFn/{fn_id}"
    for attempt in range(1, CALL_ATTEMPTS + 1):
        try:
            async with session.post(
                url,
                data=tsr_body(payload),
                headers=headers,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                text = await response.text()
                try:
                    result, error = unwrap(json.loads(text))
                except Exception:
                    result, error = None, None
                if response.status < 400 and not busy_error(response.status, error):
                    return result, error
        except Exception:
            pass
        if attempt < CALL_ATTEMPTS:
            countdown(CALL_RETRY_SECONDS * attempt, "Retry in")
    return None, None


def dashboard_of(payload):
    if isinstance(payload, dict) and isinstance(payload.get("balance"), dict):
        return payload
    return {}


def wolf_of(dashboard):
    return number_of(dashboard.get("balance"), "wolf")


def rate_of(dashboard):
    return number_of(dashboard, "wolfPerUsdt")


def usdt_text(wolf, dashboard):
    rate = rate_of(dashboard)
    if rate <= 0:
        return "0"
    return format_amount(float(wolf) / rate)


async def read_dashboard(session, account, headers, proxy):
    payload, error = await post_fn(session, FN_PROFILE, {"initData": account["initData"]}, headers, proxy)
    return dashboard_of(payload)


async def report_channel_gate(session, account, headers, proxy):
    payload, error = await post_fn(session, FN_CHANNELS, {"initData": account["initData"]}, headers, proxy)
    if not isinstance(payload, dict):
        log_yellow("Channel gate could not be checked for this account")
        return False
    if payload.get("passed"):
        log_green("Channel join is confirmed for this account")
        return True
    missing = payload.get("missing")
    name = ""
    if isinstance(missing, list) and missing:
        first = missing[0]
        if isinstance(first, dict):
            name = first.get("username") or first.get("name") or ""
    if not name:
        name = "one channel"
    log_yellow(f"Channel join is still missing for {clean_text(shorten(name, 'channel', 24), 'channel')}")
    return False


async def claim_daily_bonus(session, account, headers, proxy):
    payload, error = await post_fn(session, FN_DAILY_BONUS, {"initData": account["initData"]}, headers, proxy)
    if isinstance(payload, dict) and payload.get("reward") is not None:
        log_green(f"Daily bonus added {clean_text(format_int(payload.get('reward')), 0)} wolf")
        return True
    log_yellow("Daily bonus is already claimed today")
    return False


async def redeem_promo(session, account, headers, proxy):
    if not PROMO_CODE:
        return
    payload, error = await post_fn(
        session, FN_PROMO, {"initData": account["initData"], "code": PROMO_CODE}, headers, proxy
    )
    if isinstance(payload, dict) and payload.get("reward") is not None:
        log_green(f"Promo code credited {clean_text(format_int(payload.get('reward')), 0)} wolf")
        return
    log_yellow("Promo code was not accepted by the server")


async def claim_reward_ads(session, account, headers, proxy):
    init_data = account["initData"]
    status, error = await post_fn(session, FN_ADS_STATUS, {"initData": init_data}, headers, proxy)
    cards = status.get("cards") if isinstance(status, dict) else None
    if not isinstance(cards, list) or not cards:
        log_yellow("Ad cards were not returned by the server")
        return 0.0
    pending = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        if number_of(card, "remaining") > 0:
            pending.append(card)
    if not pending:
        log_yellow("Ad reward limit is reached for today")
        return 0.0
    earned = 0.0
    while pending:
        progressed = False
        for card in list(pending):
            card_id = str(card.get("id") or "")
            name = shorten(card.get("name"), "card", 20)
            reward = number_of(card, "reward")
            cooldown = number_of(card, "cooldown")
            if not card_id:
                pending.remove(card)
                continue
            payload, error = await post_fn(
                session, FN_AD_CLAIM, {"initData": init_data, "cardId": card_id}, headers, proxy
            )
            if isinstance(payload, dict) and payload.get("reward") is not None:
                earned += reward
                log_green(
                    f"Ad reward {clean_text(name, 'card')} credited "
                    f"{clean_text(format_int(payload.get('reward')), 0)} wolf"
                )
                progressed = True
                left = int(number_of(card, "remaining") - 1)
                card["remaining"] = left if left > 0 else 0
                if card["remaining"] <= 0:
                    log_yellow(f"Ad reward limit is reached on {clean_text(name, 'card')}")
                    pending.remove(card)
                countdown(cooldown if cooldown > 0 else IDLE_PAUSE_SECONDS, "Next ad in")
            else:
                log_yellow(
                    f"Ad reward {clean_text(name, 'card')} says "
                    f"{clean_text(reason_text(error, 'refused'), 'refused')}"
                )
                pending.remove(card)
        if not progressed or not pending:
            break
    return earned


async def work_mining_slots(session, account, headers, proxy):
    init_data = account["initData"]
    status, error = await post_fn(session, FN_MINE_STATUS, {"initData": init_data}, headers, proxy)
    if not isinstance(status, dict):
        log_yellow("Mining slots were not returned by the server")
        return 0.0
    slots = status.get("slots")
    if not isinstance(slots, list) or not slots:
        log_yellow("Mining slots are empty on this account")
        return 0.0
    limit = number_of(status, "dailyLimit")
    claims = number_of(status, "claimsToday")
    if limit > 0 and claims >= limit:
        log_yellow("Mining claim limit is reached for today")
        return 0.0
    earned = 0.0
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        number = text_of(slot, "slot", "1")
        reward = number_of(slot, "reward")
        required = int(number_of(slot, "ads"))
        done = int(number_of(slot, "adsDone"))
        ready = bool(slot.get("ready"))
        remaining = int(number_of(slot, "remaining"))
        duration = int(number_of(slot, "duration"))
        if ready:
            payload, error = await post_fn(
                session, FN_MINE_CLAIM, {"initData": init_data, "slot": int(number_of(slot, "slot", 1))},
                headers, proxy,
            )
            if isinstance(payload, dict) and payload.get("reward") is not None:
                earned += number_of(payload, "reward", reward)
                log_green(
                    f"Mining slot {clean_text(number, 1)} claim verified "
                    f"{clean_text(format_int(payload.get('reward')), 0)} wolf"
                )
            else:
                log_yellow(
                    f"Mining slot {clean_text(number, 1)} says "
                    f"{clean_text(reason_text(error, 'not ready'), 'not ready')}"
                )
            continue
        if done >= required and required > 0:
            log_yellow(
                f"Mining slot {clean_text(number, 1)} is ready in "
                f"{clean_text(format_int(remaining), 0)} seconds"
            )
            continue
        while done < required:
            payload, error = await post_fn(
                session, FN_MINE_AD, {"initData": init_data, "slot": int(number_of(slot, "slot", 1))},
                headers, proxy,
            )
            if not isinstance(payload, dict) or payload.get("adsDone") is None:
                log_yellow(
                    f"Mining slot {clean_text(number, 1)} says "
                    f"{clean_text(reason_text(error, 'refused'), 'refused')}"
                )
                break
            done = int(number_of(payload, "adsDone"))
            log_green(
                f"Mining slot {clean_text(number, 1)} ad {clean_text(format_int(done), 0)} of "
                f"{clean_text(format_int(required), 0)} counted"
            )
            time.sleep(IDLE_PAUSE_SECONDS)
        if done >= required and required > 0:
            log_yellow(
                f"Mining slot {clean_text(number, 1)} is mining for "
                f"{clean_text(format_int(duration), 0)} seconds"
            )
    return earned


async def claim_tasks(session, account, headers, proxy):
    init_data = account["initData"]
    data, error = await post_fn(session, FN_TASKS, {"initData": init_data}, headers, proxy)
    if not isinstance(data, dict):
        log_yellow("Task list was not returned by the server")
        return 0.0
    entries = []
    for key in ("main", "other"):
        group = data.get(key)
        if isinstance(group, list):
            entries.extend(group)
    earned = 0.0
    for task in entries:
        if not isinstance(task, dict) or task.get("done"):
            continue
        task_id = str(task.get("id") or "")
        title = shorten(task.get("title"), "task", 20)
        if not task_id:
            continue
        payload, error = await post_fn(
            session, FN_TASK_CLAIM, {"initData": init_data, "taskId": task_id}, headers, proxy
        )
        if isinstance(payload, dict) and payload.get("reward") is not None:
            earned += number_of(payload, "reward")
            log_green(
                f"Task {clean_text(title, 'task')} credited "
                f"{clean_text(format_int(payload.get('reward')), 0)} wolf"
            )
            time.sleep(IDLE_PAUSE_SECONDS)
            continue
        log_yellow(f"Task {clean_text(title, 'task')} says {clean_text(reason_text(error, 'refused'), 'refused')}")
    return earned


async def report_referrals(session, account, headers, proxy):
    data, error = await post_fn(session, FN_REFERRAL, {"initData": account["initData"]}, headers, proxy)
    if not isinstance(data, dict):
        log_yellow("Referral tree was not returned for this account")
        return
    log_green(
        f"Referral count is {clean_text(format_int(number_of(data, 'total')), 0)} with "
        f"{clean_text(format_int(number_of(data, 'earned')), 0)} wolf earned"
    )


async def report_gate_pass(session, account, headers, proxy):
    data, error = await post_fn(session, FN_GATE_PASS, {"initData": account["initData"]}, headers, proxy)
    if not isinstance(data, dict):
        return
    log_yellow(
        f"Withdraw pass progress is {clean_text(format_int(number_of(data, 'done')), 0)} of "
        f"{clean_text(format_int(number_of(data, 'required')), 0)}"
    )


async def report_wallet(session, account, headers, dashboard, proxy):
    data, error = await post_fn(session, FN_WALLET, {"initData": account["initData"]}, headers, proxy)
    if not isinstance(data, dict):
        log_yellow("Wallet state was not returned by the server")
        return
    config = data.get("config") if isinstance(data.get("config"), dict) else {}
    if not config.get("enabled"):
        log_yellow("Withdraw is disabled by the server")
        return
    methods = config.get("methods")
    method = methods[0] if isinstance(methods, list) and methods else {}
    method_id = str(method.get("id") or "")
    address = account.get("wallet") or PAYOUT_WALLET
    balance = wolf_of(dashboard)
    minimum = number_of(method, "minWolf")
    maximum = number_of(config, "maxWolf")
    if not address or not method_id:
        log_yellow("Withdraw stays locked until a payout wallet is set")
        return
    if minimum > 0 and balance < minimum:
        log_yellow("Withdraw stays locked until the minimum is reached")
        return
    amount = balance if maximum <= 0 or balance <= maximum else maximum
    payload, error = await post_fn(
        session,
        FN_WITHDRAW,
        {"initData": account["initData"], "method": method_id, "address": address, "wolf": amount},
        headers,
        proxy,
    )
    if isinstance(payload, dict) and payload.get("success"):
        log_green("Withdrawal request was accepted by the server")
        return
    log_yellow(f"Withdraw gate says {clean_text(reason_text(error, 'refused'), 'refused')}")


async def report_balance(session, account, headers, dashboard, proxy):
    balance = wolf_of(dashboard)
    log_green(
        f"Balance is {clean_text(format_int(balance), 0)} wolf worth "
        f"{clean_text(usdt_text(balance, dashboard), 0)} USDT"
    )


async def process_account(line, proxy, index):
    account = parse_init_data(line)
    wallet = ""
    if not account and "|" in line:
        head, tail = line.rsplit("|", 1)
        account = parse_init_data(head)
        wallet = tail.strip()
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return
    account["wallet"] = wallet

    headers = build_headers(account["initData"])
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        dashboard = await read_dashboard(session, account, headers, proxy)
        if not dashboard:
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return
        name = shorten(display_name(dashboard, account), "Runner", 20)
        log_green(
            f"Signed in {clean_text(name, 'Runner')} with "
            f"{clean_text(format_int(wolf_of(dashboard)), 0)} wolf"
        )

        gated = await report_channel_gate(session, account, headers, proxy)
        if gated:
            await claim_daily_bonus(session, account, headers, proxy)
        await redeem_promo(session, account, headers, proxy)
        await work_mining_slots(session, account, headers, proxy)
        await claim_tasks(session, account, headers, proxy)
        await claim_reward_ads(session, account, headers, proxy)
        await report_referrals(session, account, headers, proxy)
        await report_gate_pass(session, account, headers, proxy)

        fresh = await read_dashboard(session, account, headers, proxy)
        if not fresh:
            fresh = dashboard
        await report_balance(session, account, headers, fresh, proxy)
        await report_wallet(session, account, headers, fresh, proxy)
        log_yellow(f"Invite code {clean_text(REF_CODE, 'none')} is ready to share")


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1)
            countdown(ROUND_PAUSE_SECONDS, "Next account in")

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()
    sleep_secs = config.get("settings", {}).get("sleep_seconds", 3600)
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, sleep_secs))


if __name__ == "__main__":
    main()
