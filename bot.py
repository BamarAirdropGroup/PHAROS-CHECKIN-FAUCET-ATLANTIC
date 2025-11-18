
import requests
import time
import os
import random
from colorama import init, Fore
from eth_account import Account
from eth_account.messages import encode_defunct

init(autoreset=True)


try:
    CAPMONSTER_KEY = open("key.txt", "r", encoding="utf-8").read().strip()
except FileNotFoundError:
    print(Fore.RED + "key.txt not found !!")
    exit()

FAUCET_URL = "https://api.dodoex.io/gas-faucet-server/faucet/claim"
SITE_KEY = "0x4AAAAAACAb9Tup9M-ewXTN"
SITE_URL = "https://faroswap.xyz"
CHECKIN_API = "https://api.pharosnetwork.xyz"

CHECKIN_HEADERS = {
    "content-type": "application/json",
    "origin": "https://testnet.pharosnetwork.xyz",
    "referer": "https://testnet.pharosnetwork.xyz/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

FAUCET_HEADERS = {
    "content-type": "application/json",
    "origin": "https://faroswap.xyz",
    "referer": "https://faroswap.xyz/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.proxy_index = 0
        self.wallet_proxy_map = {}  

    def load_proxies(self):
        if not os.path.exists("proxy.txt"):
            print(Fore.YELLOW + "proxy.txt not found → Using Direct connection ...")
            return
        with open("proxy.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if not line.startswith(("http://", "https://", "socks4://", "socks5://")):
                    line = "http://" + line
                self.proxies.append(line)
        print(Fore.GREEN + f"Loaded {len(self.proxies)} proxies")

    def get_proxy_for_wallet(self, wallet_addr):
        if wallet_addr not in self.wallet_proxy_map:
            if not self.proxies:
                self.wallet_proxy_map[wallet_addr] = None
            else:
                proxy = self.proxies[self.proxy_index % len(self.proxies)]
                self.wallet_proxy_map[wallet_addr] = proxy
                self.proxy_index += 1
        return self.wallet_proxy_map[wallet_addr]

    def rotate_proxy_for_wallet(self, wallet_addr):
        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.wallet_proxy_map[wallet_addr] = proxy
        self.proxy_index += 1
        return proxy

    def format_proxy(self, proxy_url):
        if not proxy_url:
            return Fore.CYAN + "Direct Connection"
        if "@" in proxy_url:
            return Fore.MAGENTA + proxy_url.split("@")[-1]
        return Fore.MAGENTA + proxy_url.replace("http://", "").replace("https://", "")

proxy_manager = ProxyManager()
proxy_manager.load_proxies()

def load_accounts():
    accounts = []
    with open("accounts.txt", "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            pk = line.strip()
            if not pk: continue
            if not pk.lower().startswith("0x"): pk = "0x" + pk
            try:
                addr = Account.from_key(pk).address
                accounts.append({"address": addr, "pk": pk})
                print(Fore.CYAN + f"[{i}] {addr}")
            except:
                print(Fore.RED + f"Line {i} invalid")
    return accounts

def solve_turnstile(proxy=None):
    payload = {
        "clientKey": CAPMONSTER_KEY,
        "task": {"type": "TurnstileTaskProxyless", "websiteURL": SITE_URL, "websiteKey": SITE_KEY}
    }
    try:
        r = requests.post("https://api.capmonster.cloud/createTask", json=payload, proxies=proxy, timeout=30).json()
        if not r.get("taskId"): return None
        task_id = r["taskId"]
        for _ in range(50):
            time.sleep(4)
            res = requests.post("https://api.capmonster.cloud/getTaskResult",
                                json={"clientKey": CAPMONSTER_KEY, "taskId": task_id},
                                proxies=proxy, timeout=30).json()
            if res.get("status") == "ready":
                return res["solution"]["token"]
        return None
    except:
        return None

def daily_checkin(acc, proxy_dict=None):
    proxy_url = proxy_dict["http"] if proxy_dict else None
    try:
        message_hash = encode_defunct(text="pharos")
        signed = Account.sign_message(message_hash, acc["pk"])
        signature = signed.signature.hex()

        login_url = f"{CHECKIN_API}/user/login?address={acc['address']}&signature={signature}&invite_code=S6NGMzXSCDBxhnwo"
        login = requests.post(login_url, headers=CHECKIN_HEADERS, proxies=proxy_dict, timeout=20).json()

        if login.get("code") != 0:
            return False, login.get("msg", "Login failed")

        jwt = login["data"]["jwt"]
        checkin_url = f"{CHECKIN_API}/sign/in?address={acc['address']}"
        check = requests.post(checkin_url, headers={**CHECKIN_HEADERS, "authorization": f"Bearer {jwt}"}, proxies=proxy_dict, timeout=20).json()

        if check.get("code") == 0:
            return True, "Check-in SUCCESS"
        elif "already" in check.get("msg", "").lower():
            return True, "Already checked in"
        else:
            return False, check.get("msg")
    except Exception as e:
        return False, str(e)[:100]

def claim_faucet(acc, proxy_dict=None):
    token = solve_turnstile(proxy_dict)
    if not token:
        return False, "Turnstile failed"
    payload = {"chainId": 688689, "address": acc["address"], "turnstileToken": token}
    try:
        r = requests.post(FAUCET_URL, headers=FAUCET_HEADERS, json=payload, proxies=proxy_dict, timeout=20)
        js = r.json()
        if js.get("code") == 0:
            tx = js.get("data", {}).get("txHash", "N/A")
            return True, f"CLAIMED → https://atlantic.pharosscan.xyz/tx/{tx}"
        else:
            msg = js.get("msg", "Unknown")
            return False, msg
    except Exception as e:
        return False, str(e)[:100]


print(Fore.MAGENTA + "="*90)
print(Fore.MAGENTA + "   PHAROS AUTO BOT → CHECK-IN + FAUCET   ")
print(Fore.MAGENTA + "="*90)

accounts = load_accounts()

while True:
    for acc in accounts:
        print(Fore.MAGENTA + f"\n→ Wallet: {acc['address']}")

        
        current_proxy_url = proxy_manager.get_proxy_for_wallet(acc["address"])
        proxy_dict = {"http": current_proxy_url, "https": current_proxy_url} if current_proxy_url else None
        print(Fore.WHITE + f"   Proxy → {proxy_manager.format_proxy(current_proxy_url)}")

        
        success, msg = daily_checkin(acc, proxy_dict)
        if not success:
            print(Fore.RED + f"Check-in failed → {msg}")
            if current_proxy_url:
                print(Fore.YELLOW + "Rotating proxy...")
                new_proxy = proxy_manager.rotate_proxy_for_wallet(acc["address"])
                proxy_dict = {"http": new_proxy, "https": new_proxy} if new_proxy else None
                print(Fore.WHITE + f"   New Proxy → {proxy_manager.format_proxy(new_proxy)}")
                success, msg = daily_checkin(acc, proxy_dict)
                if success:
                    print(Fore.GREEN + f"Check-in SUCCESS after rotate → {msg}")
                else:
                    print(Fore.RED + f"Still failed → {msg}")
        else:
            print(Fore.GREEN + f"Check-in → {msg}")

        time.sleep(5)

        
        success, msg = claim_faucet(acc, proxy_dict)
        if not success:
            print(Fore.RED + f"Faucet failed → {msg}")
            if current_proxy_url:
                print(Fore.YELLOW + "Rotating proxy for faucet...")
                new_proxy = proxy_manager.rotate_proxy_for_wallet(acc["address"])
                proxy_dict = {"http": new_proxy, "https": new_proxy} if new_proxy else None
                success, msg = claim_faucet(acc, proxy_dict)
                if success:
                    print(Fore.GREEN + f"Faucet → {msg}")
                else:
                    print(Fore.RED + f"Still failed → {msg}")
        else:
            print(Fore.GREEN + f"Faucet → {msg}")

        time.sleep(10)

    print(Fore.MAGENTA + "\nAll done! Sleeping 24 hours...\n")
    time.sleep(24 * 3600)
