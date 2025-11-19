import os
import time
import random
import requests
from web3 import Web3
from eth_account.messages import encode_defunct
from fake_useragent import UserAgent
import json
from datetime import datetime
import threading


class Colors:
    RESET = '\033[0m'
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'

class Logger:
    @staticmethod
    def info(msg):
        print(f"{Colors.GREEN}[✓] {msg}{Colors.RESET}")
    
    @staticmethod
    def wallet(msg):
        print(f"{Colors.YELLOW}[➤] {msg}{Colors.RESET}")
    
    @staticmethod
    def warn(msg):
        print(f"{Colors.YELLOW}[!] {msg}{Colors.RESET}")
    
    @staticmethod
    def error(msg):
        print(f"{Colors.RED}[✗] {msg}{Colors.RESET}")
    
    @staticmethod
    def success(msg):
        print(f"{Colors.GREEN}[+] {msg}{Colors.RESET}")
    
    @staticmethod
    def loading(msg):
        print(f"{Colors.CYAN}[⟳] {msg}{Colors.RESET}")
    
    @staticmethod
    def step(msg):
        print(f"{Colors.WHITE}[➤] {msg}{Colors.RESET}")
    
    @staticmethod
    def user(msg):
        print(f"\n{Colors.WHITE}[➤] {msg}{Colors.RESET}")
    
    @staticmethod
    def proxy(msg):
        print(f"{Colors.CYAN}[🔄] {msg}{Colors.RESET}")
    
    @staticmethod
    def retry(msg):
        print(f"{Colors.YELLOW}[🔄] {msg}{Colors.RESET}")
    
    @staticmethod
    def banner():
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("-------------------------------------------------")
        print(" Pharos Daily Check-In & Faucet Claim Bot")
        print("          No need capmonster ")
        print("-------------------------------------------------")
        print(f"{Colors.RESET}\n")


PROXY_OPTIONS = {
    'MONOSAN': 1,
    'PRIVATE': 2,
    'NONE': 3
}

MONOSAN_PROXY_URL = 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt'
PROXY_FILE = 'proxies.txt'
ACCOUNTS_FILE = 'accounts.txt'


NETWORK_CONFIG = {
    'name': 'Pharos Testnet',
    'chain_id': 688689,
    'rpc_urls': [
        'https://atlantic.dplabs-internal.com/',
        'https://rpc.pharosnetwork.xyz'
    ],
    'api_url': 'https://api.pharosnetwork.xyz'
}

class ProxyManager:
    def __init__(self, use_proxy_choice):
        self.use_proxy_choice = use_proxy_choice
        self.proxies = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.load_proxies()
    
    def load_proxies(self):
        try:
            if self.use_proxy_choice == PROXY_OPTIONS['MONOSAN']:
                Logger.info('Loading Monosan proxies...')
                response = requests.get(MONOSAN_PROXY_URL, timeout=30)
                self.proxies = [line.strip() for line in response.text.split('\n') if line.strip()]
                Logger.success(f'Loaded {len(self.proxies)} Monosan proxies')
            
            elif self.use_proxy_choice == PROXY_OPTIONS['PRIVATE']:
                try:
                    Logger.info('Loading private proxies from proxies.txt...')
                    with open(PROXY_FILE, 'r', encoding='utf-8') as f:
                        raw_proxies = [line.strip() for line in f.readlines() if line.strip()]
                    
                    
                    self.proxies = []
                    for proxy in raw_proxies:
                        if self.is_valid_proxy_format(proxy):
                            self.proxies.append(proxy)
                        else:
                            Logger.warn(f'Invalid proxy format skipped: {proxy}')
                    
                    if self.proxies:
                        Logger.success(f'Loaded {len(self.proxies)} valid private proxies')
                        
                        for i, proxy in enumerate(self.proxies[:3]):
                            Logger.info(f'Proxy {i+1}: {proxy.split("@")[1] if "@" in proxy else proxy}')
                    else:
                        raise Exception('No valid proxies found in proxies.txt')
                except Exception as e:
                    Logger.warn('Failed to load private proxies, falling back to direct connection')
                    self.proxies = []
            
            else:
                Logger.info('Proxy usage disabled')
                self.proxies = []
                
        except Exception as e:
            Logger.error(f'Failed to load proxies: {str(e)}')
            self.proxies = []
    
    def is_valid_proxy_format(self, proxy):
        """Check if proxy has valid format (ip:port or user:pass@ip:port)"""
        if not proxy or ':' not in proxy:
            return False
        
        
        if '@' in proxy:
            parts = proxy.split('@')
            if len(parts) != 2:
                return False
            auth_part = parts[0]
            host_part = parts[1]
            
            
            if ':' not in auth_part:
                return False
            
            
            if ':' not in host_part:
                return False
            
            try:
                ip, port = host_part.split(':')
                int(port)  
            except:
                return False
        else:
            
            try:
                ip, port = proxy.split(':')
                int(port)  
            except:
                return False
        
        return True
    
    def get_next_proxy(self):
        if not self.proxies or len(self.proxies) == 0:
            return None
        
        
        if len(self.failed_proxies) >= len(self.proxies):
            Logger.warn("All proxies failed, resetting failed list")
            self.failed_proxies.clear()
        
        
        for _ in range(len(self.proxies)):
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            if proxy not in self.failed_proxies:
                return proxy
        
       
        return self.proxies[self.current_proxy_index]
    
    def mark_proxy_failed(self, proxy):
        if proxy:
            self.failed_proxies.add(proxy)
            Logger.proxy(f'Marked proxy as failed: {proxy.split("@")[1] if "@" in proxy else proxy}')
    
    def mark_proxy_success(self, proxy):
        if proxy in self.failed_proxies:
            self.failed_proxies.remove(proxy)
    
    def get_available_proxy_count(self):
        return len(self.proxies) - len(self.failed_proxies)
    
    def format_proxy_url(self, proxy):
        """Convert proxy string to proper requests proxy format"""
        if not proxy:
            return None
        
        
        if '@' in proxy:
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        else:
            
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }

class PharosBot:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.proxy_manager = None
        
    def sleep(self, ms):
        time.sleep(ms / 1000)
    
    def setup_provider(self, proxy_url=None):
        """Setup Web3 provider - use direct connection for RPC"""
        try:
            
            rpc_url = NETWORK_CONFIG['rpc_urls'][0]
            
            Logger.info('Using direct connection for RPC')
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
            
            
            if w3.is_connected():
                block_number = w3.eth.block_number
                Logger.info(f'Connected to network - Block: {block_number}')
                return w3
            else:
                
                Logger.warn('Primary RPC failed, trying backup...')
                rpc_url = NETWORK_CONFIG['rpc_urls'][1]
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
                
                if w3.is_connected():
                    block_number = w3.eth.block_number
                    Logger.info(f'Connected to backup network - Block: {block_number}')
                    return w3
                else:
                    raise Exception("Failed to connect to any RPC endpoint")
            
        except Exception as e:
            Logger.error(f'Provider setup failed: {str(e)}')
            raise e
    
    def get_headers(self):
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.8",
            "authorization": "Bearer null",
            "sec-ch-ua": '"Chromium";v="136", "Brave";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "sec-gpc": "1",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "User-Agent": self.ua.random,
        }
    
    def make_request_with_retry(self, request_func, max_retries=15, operation_name="API Request"):
        """Generic retry mechanism for API requests"""
        for attempt in range(max_retries):
            proxy_str = self.proxy_manager.get_next_proxy() if self.proxy_manager else None
            proxy_url = self.proxy_manager.format_proxy_url(proxy_str) if proxy_str else None
            
            try:
                if proxy_str:
                    Logger.proxy(f'Attempt {attempt + 1}/{max_retries} with proxy: {proxy_str.split("@")[1] if "@" in proxy_str else proxy_str}')
                else:
                    Logger.proxy(f'Attempt {attempt + 1}/{max_retries} with direct connection')
                
                result = request_func(proxy_url)
                
                
                if proxy_str:
                    self.proxy_manager.mark_proxy_success(proxy_str)
                
                return result
                
            except requests.exceptions.ProxyError as e:
                if proxy_str:
                    self.proxy_manager.mark_proxy_failed(proxy_str)
                    available_count = self.proxy_manager.get_available_proxy_count()
                    Logger.retry(f'Proxy error. Available proxies: {available_count}')
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
                    
            except requests.exceptions.ConnectionError as e:
                if proxy_str:
                    self.proxy_manager.mark_proxy_failed(proxy_str)
                    available_count = self.proxy_manager.get_available_proxy_count()
                    Logger.retry(f'Connection error. Available proxies: {available_count}')
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
                    
            except Exception as e:
                
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['already signed in', 'already checked in', 'already claimed', 'not available yet']):
                    Logger.warn(f'No retry needed: {e}')
                    return "ALREADY_DONE"
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)
                    Logger.retry(f'{operation_name} failed (attempt {attempt + 1}/{max_retries}): {str(e)}')
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        return None
    
    def perform_check_in(self, wallet, max_retries=15):
        wallet_address = wallet.address.lower()
        
        def check_in_request(proxy_url):
            Logger.step(f'Performing daily check-in for wallet: {wallet_address}')
            
            message = "pharos"
            message_hash = encode_defunct(text=message)
            signed_message = wallet.sign_message(message_hash)
            signature = signed_message.signature.hex()
            
            login_url = f"{NETWORK_CONFIG['api_url']}/user/login?address={wallet_address}&signature={signature}&invite_code=S6NGMzXSCDBxhnwo"
            
            headers = self.get_headers()
            
            login_response = self.session.post(
                login_url,
                headers=headers,
                proxies=proxy_url,
                timeout=30
            )
            login_data = login_response.json()
            
            if login_data.get('code') != 0 or not login_data.get('data', {}).get('jwt'):
                raise Exception(login_data.get('msg', 'Login failed'))
            
            jwt = login_data['data']['jwt']
            
            check_in_url = f"{NETWORK_CONFIG['api_url']}/sign/in?address={wallet_address}"
            check_in_response = self.session.post(
                check_in_url,
                headers={**headers, "authorization": f"Bearer {jwt}"},
                proxies=proxy_url,
                timeout=30
            )
            
            check_in_data = check_in_response.json()
            
            if check_in_data.get('code') == 0:
                Logger.success(f'✅ Daily check-in successful for {wallet_address}')
                points = check_in_data.get('data', {}).get('points', 'Unknown')
                Logger.info(f'Points awarded: {points}')
                return "SUCCESS"
            elif 'already checked in' in check_in_data.get('msg', '') or 'already signed in' in check_in_data.get('msg', ''):
                Logger.warn(f'🔄 Already checked in today for {wallet_address}')
                return "ALREADY_DONE"
            else:
                raise Exception(check_in_data.get('msg', 'Check-in failed'))
        
        try:
            result = self.make_request_with_retry(
                check_in_request, 
                max_retries, 
                "Check-in"
            )
            
            if result == "ALREADY_DONE":
                return "ALREADY_DONE"
            elif result == "SUCCESS":
                return "SUCCESS"
            else:
                return None
                
        except Exception as e:
            Logger.error(f'Check-in failed after {max_retries} retries: {str(e)}')
            return None
    
    def claim_faucet(self, wallet, max_retries=15):
        def faucet_request(proxy_url):
            Logger.step(f'Checking faucet for wallet: {wallet.address}')
            
            message = "pharos"
            message_hash = encode_defunct(text=message)
            signed_message = wallet.sign_message(message_hash)
            signature = signed_message.signature.hex()

            
            login_url = f"{NETWORK_CONFIG['api_url']}/user/login?address={wallet.address}&signature={signature}&invite_code=S6NGMzXSCDBxhnwo"

            common_headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "origin": "https://testnet.pharosnetwork.xyz",
                "referer": "https://testnet.pharosnetwork.xyz/",
                "user-agent": self.ua.random,
            }

            login_response = self.session.post(
                login_url,
                headers={**common_headers, "authorization": "Bearer null"},
                proxies=proxy_url,
                timeout=30
            )

            login_data = login_response.json()
            if login_data.get('code') != 0 or not login_data.get('data', {}).get('jwt'):
                raise Exception(login_data.get('msg', 'Login failed'))
            
            jwt = login_data['data']['jwt']

            
            status_url = f"{NETWORK_CONFIG['api_url']}/faucet/status?address={wallet.address}"
            status_response = self.session.get(
                status_url,
                headers={
                    **common_headers,
                    "authorization": f"Bearer {jwt}",
                    "priority": "u=1, i",
                },
                proxies=proxy_url,
                timeout=30
            )

            status_data = status_response.json()
            if status_data.get('code') != 0:
                raise Exception(status_data.get('msg', 'Faucet status error'))

            if not status_data.get('data', {}).get('is_able_to_faucet'):
                available_timestamp = status_data.get('data', {}).get('avaliable_timestamp')
                if available_timestamp:
                    next_time = datetime.fromtimestamp(available_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    next_time = 'Unknown'
                Logger.warn(f'❌ Faucet not available yet → Next claim: {next_time}')
                return "ALREADY_DONE"

            Logger.info('✅ Faucet is available! Claiming now...')

            
            claim_url = f"{NETWORK_CONFIG['api_url']}/faucet/daily"
            claim_response = self.session.post(
                claim_url,
                headers={
                    **common_headers,
                    "authorization": f"Bearer {jwt}",
                    "content-type": "application/json",
                    "priority": "u=1, i",
                },
                json={"address": wallet.address},
                proxies=proxy_url,
                timeout=30
            )

            claim_data = claim_response.json()
            if claim_data.get('code') == 0:
                Logger.success(f'🚰 Faucet claimed successfully → {wallet.address}')
                return "SUCCESS"
            else:
                
                if 'already' in claim_data.get('msg', '').lower():
                    Logger.warn(f'🔄 Faucet already claimed for {wallet.address}')
                    return "ALREADY_DONE"
                else:
                    raise Exception(claim_data.get('msg', 'Claim failed'))
        
        try:
            result = self.make_request_with_retry(
                faucet_request,
                max_retries,
                "Faucet claim"
            )
            
            if result == "ALREADY_DONE":
                return "ALREADY_DONE"
            elif result == "SUCCESS":
                return "SUCCESS"
            else:
                return None
                
        except Exception as e:
            Logger.error(f'Faucet process failed after {max_retries} retries: {str(e)}')
            return None
    
    def load_accounts(self):
        """Load private keys from accounts.txt"""
        try:
            if not os.path.exists(ACCOUNTS_FILE):
                Logger.error(f'{ACCOUNTS_FILE} not found!')
                return []
            
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                accounts = [line.strip() for line in f.readlines() if line.strip()]
            
            Logger.success(f'Loaded {len(accounts)} accounts from {ACCOUNTS_FILE}')
            return accounts
            
        except Exception as e:
            Logger.error(f'Failed to load accounts: {str(e)}')
            return []
    
    def countdown(self, hours):
        total_seconds = hours * 60 * 60
        Logger.info(f'Starting {hours}-hour countdown until next check...')
        
        for seconds in range(total_seconds, -1, -1):
            hrs = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = seconds % 60
            print(f'\r{Colors.CYAN}Time remaining: {hrs}h {mins}m {secs}s{Colors.RESET} ', end='', flush=True)
            time.sleep(1)
        
        print('\rCountdown complete! Checking again...')

    def run(self):
        Logger.banner()
        
        print(f'{Colors.WHITE}Select proxy option:')
        Logger.step('1. Monosan Public Proxies (auto-download)')
        Logger.step('2. Private Proxies (from proxies.txt) - For API calls only')
        Logger.step('3. No Proxy (direct connection)')
        
        try:
            proxy_choice = int(input(f'{Colors.WHITE}Enter choice (1-3): {Colors.RESET}') or '2')
        except:
            proxy_choice = 2
        
        
        self.proxy_manager = ProxyManager(proxy_choice)
        
        accounts = self.load_accounts()
        
        if not accounts:
            Logger.error('No valid accounts found in accounts.txt')
            return
        
        
        max_retries = 15
        Logger.info(f'Max retries per operation: {max_retries}')
        
        
        if proxy_choice != PROXY_OPTIONS['NONE']:
            Logger.warn('Note: Proxies will be used for API calls only, RPC uses direct connection')
        
        while True:
            try:
                successful_operations = 0
                already_done_operations = 0
                failed_operations = 0
                
                for private_key in accounts:
                    try:
                        
                        w3 = self.setup_provider()
                        wallet = w3.eth.account.from_key(private_key)
                        
                        Logger.wallet(f'Processing wallet: {wallet.address}')
                        
                        
                        check_in_result = self.perform_check_in(wallet, max_retries)
                        if check_in_result == "SUCCESS":
                            successful_operations += 1
                        elif check_in_result == "ALREADY_DONE":
                            already_done_operations += 1
                        else:
                            failed_operations += 1
                        
                        
                        faucet_result = self.claim_faucet(wallet, max_retries)
                        if faucet_result == "SUCCESS":
                            successful_operations += 1
                        elif faucet_result == "ALREADY_DONE":
                            already_done_operations += 1
                        else:
                            failed_operations += 1
                        
                        self.sleep(2000)
                        
                    except Exception as e:
                        Logger.error(f'Wallet processing error: {str(e)}')
                        failed_operations += 2
                
                
                Logger.success(f'Cycle completed: {successful_operations} successful, {already_done_operations} already done, {failed_operations} failed operations')
                
                
                self.countdown(24)
                
            except Exception as e:
                Logger.error(f'Main loop error: {str(e)}')
                time.sleep(60)

if __name__ == "__main__":
    bot = PharosBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        Logger.info('Bot stopped by user')
    except Exception as e:
        Logger.error(f'Fatal startup error: {str(e)}')
