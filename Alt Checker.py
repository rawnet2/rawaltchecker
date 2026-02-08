"""
Minecraft Alt Account Checker
Searches for Minecraft accounts/usernames on the PC
"""

import os
import json
import re
import sqlite3
import base64
import socket
import requests
from pathlib import Path
from datetime import datetime

class MinecraftAltChecker:
    def __init__(self):
        self.found_accounts = []
        self.appdata = os.getenv('APPDATA')
        self.localappdata = os.getenv('LOCALAPPDATA')
        self.userprofile = os.getenv('USERPROFILE')
        
        # Blacklist: Known false positives (not real Minecraft accounts)
        self.blacklist = {
            # Technical terms
            'init', 'oled', 'home', 'amd64', 'search_results', 'loader_manifest',
            'game_versions', 'loaders', 'true', 'false', 'null', 'none', 'default',
            'config', 'mods', 'saves', 'logs', 'resourcepacks', 'shaderpacks',
            'versions', 'assets', 'libraries', 'runtime', 'bin', 'natives',
            # Mod Loader / Modding Platforms
            'fabric', 'quilt', 'neo', 'forge', 'neoforge', 'liteloader', 'modloader',
            'optifine', 'iris', 'canvas', 'sodium', 'lithium', 'phosphor',
            # Server Software
            'bukkit', 'bungeecord', 'paper', 'purpur', 'spigot', 'velocity',
            'waterfall', 'folia', 'geyser', 'sponge',
            # Other
            'babric', 'ornithe', 'nilloader', 'datapack', 'minecraft', 'java',
            'client', 'server', 'vanilla', 'snapshot', 'release', 'beta', 'alpha',
            'main', 'test', 'debug', 'dev', 'prod', 'local', 'global', 'user',
            'player', 'guest', 'admin', 'owner', 'mod', 'staff', 'member',
            'launcher', 'profile', 'instance', 'world', 'dimension', 'biome',
        }
        
    def log(self, message, color="white"):
        """Colored console output"""
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "reset": "\033[0m"
        }
        print(f"{colors.get(color, colors['white'])}{message}{colors['reset']}")

    def add_account(self, username, source, extra_info=""):
        """Adds a found account"""
        # Ignore empty or invalid usernames
        if not username or not username.strip():
            return
        
        username = username.strip()
        
        # Ignore names that are too short or too long
        if len(username) < 3 or len(username) > 16:
            return
        
        # Check blacklist (case-insensitive)
        if username.lower() in self.blacklist:
            return
        
        # Only valid Minecraft username characters
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return
        
        # Check if username already exists
        existing = next((a for a in self.found_accounts if a['username'].lower() == username.lower()), None)
        
        if existing:
            # Add new source if not already present
            if source not in existing['source']:
                existing['source'] = existing['source'] + ", " + source
                self.log(f"  [+] Also found: {username} ({source})", "green")
        else:
            # Check if likely Bedrock account (Xbox/MS source)
            is_bedrock = "xbox" in source.lower() or "xbox/ms" in source.lower()
            
            account = {
                "username": username,
                "source": source,
                "extra_info": extra_info,
                "uuid": None,
                "is_bedrock": is_bedrock,
                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.found_accounts.append(account)
            self.log(f"  [+] Found: {username} ({source})", "green")

    def check_official_minecraft(self):
        """Checks the official Minecraft Launcher"""
        self.log("\n[*] Searching in official Minecraft Launcher...", "cyan")
        
        minecraft_path = os.path.join(self.appdata, ".minecraft")
        
        # launcher_profiles.json
        profiles_path = os.path.join(minecraft_path, "launcher_profiles.json")
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Authentication data
                if 'authenticationDatabase' in data:
                    for user_id, user_data in data['authenticationDatabase'].items():
                        if 'displayName' in user_data:
                            self.add_account(user_data['displayName'], "Minecraft Launcher (authenticationDatabase)")
                        if 'username' in user_data:
                            self.add_account(user_data['username'], "Minecraft Launcher (authenticationDatabase)")
                            
                # Profiles
                if 'profiles' in data:
                    for profile_id, profile_data in data['profiles'].items():
                        if 'name' in profile_data:
                            self.add_account(profile_data['name'], "Minecraft Launcher (Profile)")
                            
            except Exception as e:
                self.log(f"  [-] Error reading launcher_profiles.json: {e}", "red")

        # launcher_accounts.json (newer versions) - different variants
        account_files = [
            "launcher_accounts.json",
            "launcher_accounts_microsoft_store.json",
        ]
        
        for acc_file in account_files:
            accounts_path = os.path.join(minecraft_path, acc_file)
            if os.path.exists(accounts_path):
                try:
                    with open(accounts_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    if 'accounts' in data:
                        for acc_id, acc_data in data['accounts'].items():
                            if 'minecraftProfile' in acc_data:
                                profile = acc_data['minecraftProfile']
                                if 'name' in profile:
                                    self.add_account(profile['name'], f"Minecraft Launcher ({acc_file})")
                            if 'username' in acc_data:
                                self.add_account(acc_data['username'], f"Minecraft Launcher ({acc_file}) - Xbox/MS")
                                
                except Exception as e:
                    self.log(f"  [-] Error reading {acc_file}: {e}", "red")

        # launcher_profiles_microsoft_store.json
        ms_profiles_path = os.path.join(minecraft_path, "launcher_profiles_microsoft_store.json")
        if os.path.exists(ms_profiles_path):
            try:
                with open(ms_profiles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'profiles' in data:
                    for profile_id, profile_data in data['profiles'].items():
                        if 'name' in profile_data:
                            self.add_account(profile_data['name'], "Minecraft MS Store")
            except:
                pass

    def check_tlauncher(self):
        """Checks TLauncher"""
        self.log("\n[*] Searching in TLauncher...", "cyan")
        
        tlauncher_paths = [
            os.path.join(self.appdata, ".tlauncher"),
            os.path.join(self.appdata, "tlauncher"),
            os.path.join(self.userprofile, ".tlauncher"),
        ]
        
        for tl_path in tlauncher_paths:
            if os.path.exists(tl_path):
                # TLauncher.cfg
                cfg_path = os.path.join(tl_path, "TLauncher.cfg")
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Search for login= or username=
                            matches = re.findall(r'(?:login|username|client\.username)=([^\n\r]+)', content)
                            for match in matches:
                                if match.strip():
                                    self.add_account(match.strip(), "TLauncher")
                    except:
                        pass
                        
                # accounts.json
                accounts_path = os.path.join(tl_path, "accounts.json")
                if os.path.exists(accounts_path):
                    try:
                        with open(accounts_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for acc in data:
                                    if 'username' in acc:
                                        self.add_account(acc['username'], "TLauncher")
                            elif isinstance(data, dict):
                                for key, acc in data.items():
                                    if isinstance(acc, dict) and 'username' in acc:
                                        self.add_account(acc['username'], "TLauncher")
                    except:
                        pass

    def check_multimc(self):
        """Checks MultiMC and PolyMC"""
        self.log("\n[*] Searching in MultiMC/PolyMC...", "cyan")
        
        multimc_paths = [
            os.path.join(self.appdata, "MultiMC"),
            os.path.join(self.localappdata, "MultiMC"),
            os.path.join(self.appdata, "PolyMC"),
            os.path.join(self.localappdata, "PolyMC"),
            os.path.join(self.appdata, "PrismLauncher"),
            os.path.join(self.localappdata, "PrismLauncher"),
        ]
        
        for mmc_path in multimc_paths:
            if os.path.exists(mmc_path):
                # accounts.json
                accounts_path = os.path.join(mmc_path, "accounts.json")
                if os.path.exists(accounts_path):
                    try:
                        with open(accounts_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'accounts' in data:
                                for acc in data['accounts']:
                                    if 'profile' in acc and 'name' in acc['profile']:
                                        self.add_account(acc['profile']['name'], f"MultiMC/PolyMC ({os.path.basename(mmc_path)})")
                    except:
                        pass

    def check_lunar_client(self):
        """Checks Lunar Client"""
        self.log("\n[*] Searching in Lunar Client...", "cyan")
        
        lunar_paths = [
            os.path.join(self.userprofile, ".lunarclient"),
            os.path.join(self.appdata, ".lunarclient"),
        ]
        
        for lunar_path in lunar_paths:
            if os.path.exists(lunar_path):
                # settings/game/accounts.json
                accounts_path = os.path.join(lunar_path, "settings", "game", "accounts.json")
                if os.path.exists(accounts_path):
                    try:
                        with open(accounts_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'accounts' in data:
                                for acc in data['accounts']:
                                    if 'minecraftProfile' in acc and 'name' in acc['minecraftProfile']:
                                        self.add_account(acc['minecraftProfile']['name'], "Lunar Client")
                    except:
                        pass
                        
                # launcher-accounts.json
                launcher_acc = os.path.join(lunar_path, "launcher-accounts.json")
                if os.path.exists(launcher_acc):
                    try:
                        with open(launcher_acc, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                for key, acc in data.items():
                                    if isinstance(acc, dict):
                                        if 'name' in acc:
                                            self.add_account(acc['name'], "Lunar Client")
                    except:
                        pass

    def check_badlion(self):
        """Checks Badlion Client"""
        self.log("\n[*] Searching in Badlion Client...", "cyan")
        
        badlion_path = os.path.join(self.appdata, "Badlion Client")
        if os.path.exists(badlion_path):
            # accounts.json
            accounts_path = os.path.join(badlion_path, "accounts.json")
            if os.path.exists(accounts_path):
                try:
                    with open(accounts_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for acc in data:
                                if 'username' in acc:
                                    self.add_account(acc['username'], "Badlion Client")
                except:
                    pass

    def check_feather(self):
        """Checks Feather Client"""
        self.log("\n[*] Searching in Feather Client...", "cyan")
        
        feather_paths = [
            os.path.join(self.appdata, ".feather"),
            os.path.join(self.userprofile, ".feather"),
        ]
        
        for feather_path in feather_paths:
            if os.path.exists(feather_path):
                accounts_path = os.path.join(feather_path, "accounts.json")
                if os.path.exists(accounts_path):
                    try:
                        with open(accounts_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'accounts' in data:
                                for acc in data['accounts']:
                                    if 'profile' in acc and 'name' in acc['profile']:
                                        self.add_account(acc['profile']['name'], "Feather Client")
                    except:
                        pass

    def check_labymod(self):
        """Checks LabyMod"""
        self.log("\n[*] Searching in LabyMod...", "cyan")
        
        labymod_path = os.path.join(self.appdata, ".labymod")
        if os.path.exists(labymod_path):
            # accounts.json
            accounts_path = os.path.join(labymod_path, "accounts.json")
            if os.path.exists(accounts_path):
                try:
                    with open(accounts_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for acc in data:
                                if 'username' in acc:
                                    self.add_account(acc['username'], "LabyMod")
                except:
                    pass

    def check_curseforge(self):
        """Checks CurseForge/Overwolf"""
        self.log("\n[*] Searching in CurseForge...", "cyan")
        
        curseforge_path = os.path.join(self.appdata, "curseforge")
        if os.path.exists(curseforge_path):
            # Search for account files
            for root, dirs, files in os.walk(curseforge_path):
                for file in files:
                    if 'account' in file.lower() and file.endswith('.json'):
                        try:
                            filepath = os.path.join(root, file)
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                self._extract_usernames_recursive(data, "CurseForge")
                        except:
                            pass

    def check_atlauncher(self):
        """Checks ATLauncher"""
        self.log("\n[*] Searching in ATLauncher...", "cyan")
        
        atlauncher_path = os.path.join(self.appdata, "ATLauncher")
        if os.path.exists(atlauncher_path):
            # launcher.json
            launcher_path = os.path.join(atlauncher_path, "launcher.json")
            if os.path.exists(launcher_path):
                try:
                    with open(launcher_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'account' in data:
                            if 'minecraftUsername' in data['account']:
                                self.add_account(data['account']['minecraftUsername'], "ATLauncher")
                except:
                    pass

    def check_technic(self):
        """Checks Technic Launcher"""
        self.log("\n[*] Searching in Technic Launcher...", "cyan")
        
        technic_path = os.path.join(self.appdata, ".technic")
        if os.path.exists(technic_path):
            # launcher.properties
            props_path = os.path.join(technic_path, "launcher.properties")
            if os.path.exists(props_path):
                try:
                    with open(props_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = re.findall(r'(?:username|displayName)=([^\n\r]+)', content)
                        for match in matches:
                            if match.strip():
                                self.add_account(match.strip(), "Technic Launcher")
                except:
                    pass

    def check_modrinth(self):
        """Checks Modrinth App"""
        self.log("\n[*] Searching in Modrinth App...", "cyan")
        
        modrinth_path = os.path.join(self.appdata, "ModrinthApp")
        if os.path.exists(modrinth_path):
            # NOTE: usercache.json does NOT contain your own account, but rather
            # other players seen on servers - therefore this file is NOT processed
            # to avoid false positives.
            
            # Search for accounts.json or similar account files
            account_files = [
                os.path.join(modrinth_path, "accounts.json"),
                os.path.join(modrinth_path, "launcher", "accounts.json"),
                os.path.join(modrinth_path, "config", "accounts.json"),
            ]
            
            for acc_file in account_files:
                if os.path.exists(acc_file):
                    try:
                        with open(acc_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self._extract_usernames_recursive(data, "Modrinth App")
                    except:
                        pass
            
            # SQLite database - minecraft_users table contains logged in accounts
            db_path = os.path.join(modrinth_path, "app.db")
            if os.path.exists(db_path):
                try:
                    # Use read-only URI mode to avoid locking issues
                    db_uri = f"file:{db_path}?mode=ro"
                    conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
                    cursor = conn.cursor()
                    
                    # Query the minecraft_users table directly (contains Minecraft accounts)
                    try:
                        rows = cursor.execute("SELECT username FROM minecraft_users").fetchall()
                        for row in rows:
                            if row[0]:
                                self.add_account(row[0], "Modrinth App")
                    except Exception as e:
                        self.log(f"  [-] SQL query error: {e}", "yellow")
                    
                    conn.close()
                except Exception as e:
                    self.log(f"  [-] Error reading Modrinth DB: {e}", "red")


    def check_logs(self):
        """Checks Minecraft logs for usernames"""
        self.log("\n[*] Searching in Minecraft Logs...", "cyan")
        
        logs_path = os.path.join(self.appdata, ".minecraft", "logs")
        if os.path.exists(logs_path):
            for file in os.listdir(logs_path):
                if file.endswith('.log') or file.endswith('.log.gz'):
                    try:
                        filepath = os.path.join(logs_path, file)
                        if file.endswith('.gz'):
                            import gzip
                            with gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        else:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        
                        # Search for "Setting user: USERNAME"
                        matches = re.findall(r'Setting user: ([A-Za-z0-9_]+)', content)
                        for match in matches:
                            self.add_account(match, "Minecraft Logs")
                            
                        # Search for "[Client thread/INFO]: Connecting to"
                        matches = re.findall(r'\[Client thread/INFO\]: ([A-Za-z0-9_]+) \(Session ID', content)
                        for match in matches:
                            self.add_account(match, "Minecraft Logs")
                    except:
                        pass

    def _extract_usernames_recursive(self, data, source, depth=0):
        """Extracts usernames recursively from JSON data"""
        if depth > 10:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['username', 'name', 'displayname', 'playername', 'minecraftusername']:
                    if isinstance(value, str) and 3 <= len(value) <= 16:
                        # Minecraft usernames: 3-16 characters, alphanumeric + underscore
                        if re.match(r'^[A-Za-z0-9_]+$', value):
                            self.add_account(value, source)
                else:
                    self._extract_usernames_recursive(value, source, depth + 1)
        elif isinstance(data, list):
            for item in data:
                self._extract_usernames_recursive(item, source, depth + 1)

    def deep_search(self):
        """Deep search for additional Minecraft-related files"""
        self.log("\n[*] Performing deep search...", "cyan")
        
        search_paths = [
            self.appdata,
            self.localappdata,
        ]
        
        keywords = ['minecraft', 'launcher', 'multimc', 'tlauncher', 'lunar', 'badlion', 'feather']
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
                
            try:
                for item in os.listdir(search_path):
                    item_lower = item.lower()
                    if any(kw in item_lower for kw in keywords):
                        full_path = os.path.join(search_path, item)
                        if os.path.isdir(full_path):
                            self._search_directory_for_accounts(full_path)
            except:
                pass

    def _search_directory_for_accounts(self, directory, depth=0):
        """Searches a directory for account files"""
        if depth > 3:
            return
            
        try:
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                
                if os.path.isfile(full_path):
                    if item.endswith('.json') and 'account' in item.lower():
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                self._extract_usernames_recursive(data, f"Deep Search ({directory})")
                        except:
                            pass
                            
                elif os.path.isdir(full_path):
                    self._search_directory_for_accounts(full_path, depth + 1)
        except:
            pass

    def export_results(self):
        """Exports the results to a file"""
        if not self.found_accounts:
            return
            
        # Export as JSON
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "found_accounts.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.found_accounts, f, indent=2, ensure_ascii=False)
        self.log(f"\n[+] Results exported to: {output_path}", "green")
        
        # Export as text
        txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "found_accounts.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("MINECRAFT ALT ACCOUNT CHECKER - RESULTS\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            # Group by source
            sources = {}
            for acc in self.found_accounts:
                source = acc['source']
                if source not in sources:
                    sources[source] = []
                sources[source].append(acc['username'])
            
            for source, usernames in sources.items():
                f.write(f"\n[{source}]\n")
                f.write("-" * 40 + "\n")
                for username in usernames:
                    f.write(f"  • {username}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"Total found: {len(self.found_accounts)} accounts\n")
        
        self.log(f"[+] Text file exported to: {txt_path}", "green")

    def check_name_history(self, username):
        """Checks external databases for old usernames that may have been changed"""
        
        # Try Ashcon API - stores name history and old names
        try:
            response = requests.get(
                f"https://api.ashcon.app/mojang/v2/user/{username}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                uuid = data.get('uuid', '')
                current_name = data.get('username', '')
                if uuid and current_name:
                    return {
                        'current_name': current_name,
                        'uuid': uuid,
                        'old_name': username if current_name.lower() != username.lower() else None
                    }
        except:
            pass
        
        # Try Minetools API
        try:
            response = requests.get(
                f"https://api.minetools.eu/uuid/{username}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') != 'ERR':
                    uuid = data.get('id', '')
                    current_name = data.get('name', '')
                    if uuid and current_name:
                        # Format UUID with dashes
                        if len(uuid) == 32:
                            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                        return {
                            'current_name': current_name,
                            'uuid': uuid,
                            'old_name': username if current_name.lower() != username.lower() else None
                        }
        except:
            pass
        
        # Try PlayerDB API - it stores name history
        try:
            response = requests.get(
                f"https://playerdb.co/api/player/minecraft/{username}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('player', {}):
                    player = data['data']['player']
                    current_name = player.get('username')
                    uuid = player.get('id', '')
                    if current_name and uuid:
                        # Format UUID with dashes if needed
                        if len(uuid) == 32:
                            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                        return {
                            'current_name': current_name,
                            'uuid': uuid,
                            'old_name': username if current_name.lower() != username.lower() else None
                        }
        except:
            pass
        
        # Try Laby.net API as fallback
        try:
            response = requests.get(
                f"https://laby.net/api/user/{username}/get-uuid",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                uuid = data.get('uuid', '')
                if uuid:
                    # Format UUID with dashes
                    uuid_formatted = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}" if len(uuid) == 32 else uuid
                    # Get current name from Mojang with UUID
                    try:
                        name_response = requests.get(
                            f"https://api.mojang.com/user/profile/{uuid}",
                            timeout=5
                        )
                        if name_response.status_code == 200:
                            profile = name_response.json()
                            current_name = profile.get('name', username)
                            return {
                                'current_name': current_name,
                                'uuid': uuid_formatted,
                                'old_name': username if current_name.lower() != username.lower() else None
                            }
                    except:
                        pass
        except:
            pass
        
        return None

    def fetch_uuids(self):
        """Fetches UUIDs for all found accounts from Mojang API"""
        self.log("\n[*] Fetching UUIDs from Mojang API...", "cyan")
        
        for acc in self.found_accounts:
            if acc.get('uuid'):
                continue  # Already has UUID
            
            try:
                response = requests.get(
                    f"https://api.mojang.com/users/profiles/minecraft/{acc['username']}",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    uuid = data.get('id', '')
                    # Format UUID with dashes
                    if len(uuid) == 32:
                        uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                    acc['uuid'] = uuid
                    acc['is_bedrock'] = False  # Has Java UUID, not Bedrock-only
                    self.log(f"  [+] {acc['username']}: {uuid}", "green")
                else:
                    # No Java UUID found - if Xbox source, it's Bedrock
                    if acc.get('is_bedrock'):
                        acc['uuid'] = "No UUID (Bedrock account)"
                        self.log(f"  [!] {acc['username']}: No UUID (Bedrock account)", "yellow")
                    else:
                        # Try to find in external databases (name might have changed)
                        self.log(f"  [?] {acc['username']}: Checking external databases...", "yellow")
                        history_result = self.check_name_history(acc['username'])
                        
                        if history_result:
                            acc['uuid'] = history_result['uuid']
                            acc['is_bedrock'] = False
                            if history_result['old_name']:
                                # Name was changed - update to current name
                                old_name = acc['username']
                                acc['username'] = history_result['current_name']
                                acc['name_updated'] = True
                                acc['old_name'] = old_name
                                self.log(f"  [+] {old_name} -> {history_result['current_name']}: {history_result['uuid']} (Name Updated!)", "green")
                            else:
                                self.log(f"  [+] {acc['username']}: {history_result['uuid']} (Found in DB)", "green")
                        else:
                            acc['uuid'] = "Not found (Name changed?)"
                            self.log(f"  [-] {acc['username']}: Not found in any database", "yellow")
            except Exception as e:
                acc['uuid'] = "Error fetching"
                self.log(f"  [-] {acc['username']}: Error - {e}", "red")

    def send_to_discord(self):
        """Sends results to Discord webhook with a clean embed"""
        if not self.found_accounts:
            return
        
        webhook_url = "ENTER YOU WEBHOOK URL HERE!"
        
        try:
            # Get system info
            hostname = socket.gethostname()
            username = os.getenv('USERNAME', 'Unknown')
            
            # Deduplicate accounts by UUID
            seen_uuids = set()
            unique_accounts = []
            for acc in self.found_accounts:
                uuid = acc.get('uuid', '')
                # Skip if we've already seen this UUID (and it's a valid UUID)
                if uuid and not uuid.startswith("Not found") and not uuid.startswith("Error") and not uuid.startswith("No UUID"):
                    if uuid in seen_uuids:
                        continue
                    seen_uuids.add(uuid)
                unique_accounts.append(acc)
            
            # Categorize accounts: JAVA, BEDROCK, NOT FOUND
            java_accounts = []
            bedrock_accounts = []
            not_found_accounts = []
            
            for acc in unique_accounts:
                uuid = acc.get('uuid', 'Unknown')
                if not uuid:
                    uuid = 'Unknown'
                
                if acc.get('is_bedrock'):
                    bedrock_accounts.append((acc, uuid))
                elif acc.get('uuid') and not acc['uuid'].startswith("Not found") and not acc['uuid'].startswith("Error"):
                    java_accounts.append((acc, uuid))
                else:
                    not_found_accounts.append((acc, uuid))
            
            # Build account fields in order: JAVA -> BEDROCK -> NOT FOUND
            fields = []
            
            for acc, uuid in java_accounts:
                name = f":coffee: {acc['username']} [JAVA]"
                value = f"```{uuid}```"
                # Add Updated IGN tag if name was changed
                if acc.get('name_updated'):
                    name = f":coffee: {acc['username']} [JAVA] [Updated IGN]"
                fields.append({
                    "name": name,
                    "value": value,
                    "inline": False
                })
            
            for acc, uuid in bedrock_accounts:
                fields.append({
                    "name": f":rock: {acc['username']} [BEDROCK]",
                    "value": f"```{uuid}```",
                    "inline": False
                })
            
            # Not found accounts - show with NameMC link to check manually
            for acc, uuid in not_found_accounts:
                namemc_link = f"https://namemc.com/search?q={acc['username']}"
                fields.append({
                    "name": f":question: {acc['username']} [NOT FOUND]",
                    "value": f"[Check on NameMC]({namemc_link})",
                    "inline": False
                })
            
            # Count only verified accounts
            verified_count = len(java_accounts) + len(bedrock_accounts)
            
            # Create embed
            embed = {
                "title": ":pick: Minecraft Alt Checker Results",
                "description": f"**{verified_count}** verified account(s) found\n**{len(not_found_accounts)}** unverified",
                "color": 0xFF0000,  # Red
                "fields": fields,
                "footer": {
                    "text": f"PC: {hostname} | User: {username}"
                },
                "timestamp": datetime.now().astimezone().isoformat()
            }
            
            payload = {
                "embeds": [embed],
                "username": "Minecraft Alt Checker"
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                self.log("[+] Results sent to Discord!", "green")
            else:
                self.log(f"[-] Discord webhook failed: {response.status_code}", "red")
                
        except Exception as e:
            self.log(f"[-] Failed to send to Discord: {e}", "red")

    def run(self):
        """Runs all checks"""
        self.log("=" * 60, "magenta")
        self.log("       MINECRAFT ALT ACCOUNT CHECKER", "magenta")
        self.log("=" * 60, "magenta")
        self.log(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "yellow")
        
        # Run all checks
        self.check_official_minecraft()
        self.check_tlauncher()
        self.check_multimc()
        self.check_lunar_client()
        self.check_badlion()
        self.check_feather()
        self.check_labymod()
        self.check_curseforge()
        self.check_atlauncher()
        self.check_technic()
        self.check_modrinth()
        self.check_logs()
        self.deep_search()
        
        # Display results
        self.log("\n" + "=" * 60, "magenta")
        self.log("                  RESULTS", "magenta")
        self.log("=" * 60, "magenta")
        
        if self.found_accounts:
            self.log(f"\n[+] Total {len(self.found_accounts)} account(s) found:\n", "green")
            
            # Group by source
            sources = {}
            for acc in self.found_accounts:
                source = acc['source']
                if source not in sources:
                    sources[source] = []
                sources[source].append(acc['username'])
            
            for source, usernames in sorted(sources.items()):
                self.log(f"\n  [{source}]", "cyan")
                for username in usernames:
                    self.log(f"    -> {username}", "yellow")
            
            # Fetch UUIDs and send to Discord
            self.fetch_uuids()
            self.send_to_discord()
        else:
            self.log("\n[-] No Minecraft accounts found.", "red")
        
        self.log("\n" + "=" * 60, "magenta")
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    # Enable Windows color support
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass
    
    checker = MinecraftAltChecker()
    checker.run()

