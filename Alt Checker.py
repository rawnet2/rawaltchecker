import os
import json
import re
import sqlite3
import base64
import socket
import requests
from pathlib import Path
from datetime import datetime
import sys
import time
import threading
import shutil

class MinecraftAltChecker:
    def __init__(self):
        self.found_accounts = []
        self.appdata = os.getenv('APPDATA')
        self.localappdata = os.getenv('LOCALAPPDATA')
        self.userprofile = os.getenv('USERPROFILE')
        self.silent = True
        self.pbar = None
        
        self.blacklist = {
            'init', 'oled', 'home', 'amd64', 'search_results', 'loader_manifest',
            'game_versions', 'loaders', 'true', 'false', 'null', 'none', 'default',
            'config', 'mods', 'saves', 'logs', 'resourcepacks', 'shaderpacks',
            'versions', 'assets', 'libraries', 'runtime', 'bin', 'natives',
            'fabric', 'quilt', 'neo', 'forge', 'neoforge', 'liteloader', 'modloader',
            'optifine', 'iris', 'canvas', 'sodium', 'lithium', 'phosphor',
            'bukkit', 'bungeecord', 'paper', 'purpur', 'spigot', 'velocity',
            'waterfall', 'folia', 'geyser', 'sponge',
            'babric', 'ornithe', 'nilloader', 'datapack', 'minecraft', 'java',
            'client', 'server', 'vanilla', 'snapshot', 'release', 'beta', 'alpha',
            'main', 'test', 'debug', 'dev', 'prod', 'local', 'global', 'user',
            'player', 'guest', 'admin', 'owner', 'mod', 'staff', 'member',
            'launcher', 'profile', 'instance', 'world', 'dimension', 'biome',
        }
        
    def log(self, message, color="white"):
        if self.silent:
            return
        colors = {
            "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
            "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
            "white": "\033[97m", "reset": "\033[0m"
        }
        print(f"{colors.get(color, colors['white'])}{message}{colors['reset']}")

    def add_account(self, username, source, extra_info=""):
        if not username or not username.strip():
            return
        
        username = username.strip()
        
        if len(username) < 3 or len(username) > 16:
            return
        
        if username.lower() in self.blacklist:
            return
        
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return
        
        existing = next((a for a in self.found_accounts if a['username'].lower() == username.lower()), None)
        
        if existing:
            if source not in existing['source']:
                existing['source'] = existing['source'] + ", " + source
        else:
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

    def check_official_minecraft(self):
        minecraft_path = os.path.join(self.appdata, ".minecraft")
        
        profiles_path = os.path.join(minecraft_path, "launcher_profiles.json")
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if 'authenticationDatabase' in data:
                    for user_id, user_data in data['authenticationDatabase'].items():
                        if 'displayName' in user_data:
                            self.add_account(user_data['displayName'], "Minecraft Launcher (authenticationDatabase)")
                        if 'username' in user_data:
                            self.add_account(user_data['username'], "Minecraft Launcher (authenticationDatabase)")
                            
                if 'profiles' in data:
                    for profile_id, profile_data in data['profiles'].items():
                        if 'name' in profile_data:
                            self.add_account(profile_data['name'], "Minecraft Launcher (Profile)")
                            
            except Exception as e:
                pass

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
                    pass

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
        tlauncher_paths = [
            os.path.join(self.appdata, ".tlauncher"),
            os.path.join(self.appdata, "tlauncher"),
            os.path.join(self.userprofile, ".tlauncher"),
        ]
        
        for tl_path in tlauncher_paths:
            if os.path.exists(tl_path):
                cfg_path = os.path.join(tl_path, "TLauncher.cfg")
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            matches = re.findall(r'(?:login|username|client\.username)=([^\n\r]+)', content)
                            for match in matches:
                                if match.strip():
                                    self.add_account(match.strip(), "TLauncher")
                    except:
                        pass
                        
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
        lunar_paths = [
            os.path.join(self.userprofile, ".lunarclient"),
            os.path.join(self.appdata, ".lunarclient"),
        ]
        
        for lunar_path in lunar_paths:
            if os.path.exists(lunar_path):
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
        badlion_path = os.path.join(self.appdata, "Badlion Client")
        if os.path.exists(badlion_path):
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
        labymod_path = os.path.join(self.appdata, ".labymod")
        if os.path.exists(labymod_path):
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
        curseforge_path = os.path.join(self.appdata, "curseforge")
        if os.path.exists(curseforge_path):
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
        atlauncher_path = os.path.join(self.appdata, "ATLauncher")
        if os.path.exists(atlauncher_path):
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
        technic_path = os.path.join(self.appdata, ".technic")
        if os.path.exists(technic_path):
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
        modrinth_path = os.path.join(self.appdata, "ModrinthApp")
        if os.path.exists(modrinth_path):
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
            
            db_path = os.path.join(modrinth_path, "app.db")
            if os.path.exists(db_path):
                try:
                    db_uri = f"file:{db_path}?mode=ro"
                    conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
                    cursor = conn.cursor()
                    try:
                        rows = cursor.execute("SELECT username FROM minecraft_users").fetchall()
                        for row in rows:
                            if row[0]:
                                self.add_account(row[0], "Modrinth App")
                    except:
                        pass
                    conn.close()
                except:
                    pass

    def check_logs(self):
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
                        
                        matches = re.findall(r'Setting user: ([A-Za-z0-9_]+)', content)
                        for match in matches:
                            self.add_account(match, "Minecraft Logs")
                            
                        matches = re.findall(r'\[Client thread/INFO\]: ([A-Za-z0-9_]+) \(Session ID', content)
                        for match in matches:
                            self.add_account(match, "Minecraft Logs")
                    except:
                        pass

    def _extract_usernames_recursive(self, data, source, depth=0):
        if depth > 10:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['username', 'name', 'displayname', 'playername', 'minecraftusername']:
                    if isinstance(value, str) and 3 <= len(value) <= 16:
                        if re.match(r'^[A-Za-z0-9_]+$', value):
                            self.add_account(value, source)
                else:
                    self._extract_usernames_recursive(value, source, depth + 1)
        elif isinstance(data, list):
            for item in data:
                self._extract_usernames_recursive(item, source, depth + 1)

    def deep_search(self):
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
        if not self.found_accounts:
            return
            
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "found_accounts.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.found_accounts, f, indent=2, ensure_ascii=False)
        self.log(f"\n[+] Results exported to: {output_path}", "green")
        
        txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "found_accounts.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("MINECRAFT ALT ACCOUNT CHECKER - RESULTS\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
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
                        if len(uuid) == 32:
                            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                        return {
                            'current_name': current_name,
                            'uuid': uuid,
                            'old_name': username if current_name.lower() != username.lower() else None
                        }
        except:
            pass
        
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
                        if len(uuid) == 32:
                            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                        return {
                            'current_name': current_name,
                            'uuid': uuid,
                            'old_name': username if current_name.lower() != username.lower() else None
                        }
        except:
            pass
        
        try:
            response = requests.get(
                f"https://laby.net/api/user/{username}/get-uuid",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                uuid = data.get('uuid', '')
                if uuid:
                    uuid_formatted = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}" if len(uuid) == 32 else uuid
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
        total = len(self.found_accounts)
        for i, acc in enumerate(self.found_accounts):
            if acc.get('uuid'):
                self._draw_bar("Resolving UUIDs", i + 1, total)
                continue
            
            try:
                response = requests.get(
                    f"https://api.mojang.com/users/profiles/minecraft/{acc['username']}",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    uuid = data.get('id', '')
                    if len(uuid) == 32:
                        uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                    acc['uuid'] = uuid
                    acc['is_bedrock'] = False
                else:
                    if acc.get('is_bedrock'):
                        acc['uuid'] = "No UUID (Bedrock account)"
                    else:
                        history_result = self.check_name_history(acc['username'])
                        if history_result:
                            acc['uuid'] = history_result['uuid']
                            acc['is_bedrock'] = False
                            if history_result['old_name']:
                                old_name = acc['username']
                                acc['username'] = history_result['current_name']
                                acc['name_updated'] = True
                                acc['old_name'] = old_name
                        else:
                            acc['uuid'] = "Not found (Name changed?)"
            except Exception as e:
                acc['uuid'] = "Error fetching"
            
            self._draw_bar("Resolving UUIDs", i + 1, total)

    def send_to_discord(self, webhook_url):
        if not self.found_accounts or not webhook_url:
            return
        
        try:
            hostname = socket.gethostname()
            username = os.getenv('USERNAME', 'Unknown')
            
            seen_uuids = set()
            unique_accounts = []
            for acc in self.found_accounts:
                uuid = acc.get('uuid', '')
                if uuid and not uuid.startswith("Not found") and not uuid.startswith("Error") and not uuid.startswith("No UUID"):
                    if uuid in seen_uuids:
                        continue
                    seen_uuids.add(uuid)
                unique_accounts.append(acc)
            
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
            
            fields = []
            
            for acc, uuid in java_accounts:
                name = f":coffee: {acc['username']} [JAVA]"
                value = f"```{uuid}```"
                if acc.get('name_updated'):
                    name = f":coffee: {acc['username']} [JAVA] [Updated IGN]"
                fields.append({"name": name, "value": value, "inline": False})
            
            for acc, uuid in bedrock_accounts:
                fields.append({
                    "name": f":rock: {acc['username']} [BEDROCK]",
                    "value": f"```{uuid}```",
                    "inline": False
                })
            
            for acc, uuid in not_found_accounts:
                namemc_link = f"https://namemc.com/search?q={acc['username']}"
                fields.append({
                    "name": f":question: {acc['username']} [NOT FOUND]",
                    "value": f"[Check on NameMC]({namemc_link})",
                    "inline": False
                })
            
            verified_count = len(java_accounts) + len(bedrock_accounts)
            
            embed = {
                "title": ":pick: Raw Alt Checker Results",
                "description": f"**{verified_count}** verified account(s) found\n**{len(not_found_accounts)}** unverified",
                "color": 0xA855F7,
                "fields": fields,
                "footer": {"text": f"PC: {hostname} | User: {username}"},
                "timestamp": datetime.now().astimezone().isoformat()
            }
            
            payload = {
                "embeds": [embed],
                "username": "Raw Alt Checker"
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
                
        except Exception as e:
            pass

    PURPLE  = "\033[38;5;129m"
    VIOLET  = "\033[38;5;141m"
    PINK    = "\033[38;5;213m"
    CYAN_C  = "\033[38;5;87m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"
    HIDE    = "\033[?25l"
    SHOW    = "\033[?25h"
    CLEAR   = "\033[2J\033[H"

    GRADIENT = [
        "\033[38;5;53m", "\033[38;5;54m", "\033[38;5;55m",
        "\033[38;5;56m", "\033[38;5;57m", "\033[38;5;93m",
        "\033[38;5;129m", "\033[38;5;165m", "\033[38;5;201m",
        "\033[38;5;177m", "\033[38;5;141m", "\033[38;5;105m",
    ]

    BANNER = [
        " ██████╗  █████╗ ██╗    ██╗",
        " ██╔══██╗██╔══██╗██║    ██║",
        " ██████╔╝███████║██║ █╗ ██║",
        " ██╔══██╗██╔══██║██║███╗██║",
        " ██║  ██║██║  ██║╚███╔███╔╝",
        " ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝",
    ]

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def _cols(self):
        return shutil.get_terminal_size((80, 24)).columns

    def _center(self, text, width=None):
        w = width or self._cols()
        stripped_len = len(re.sub(r'\033\[[0-9;]*m', '', text))
        pad = max(0, (w - stripped_len) // 2)
        return " " * pad + text

    def _print_banner(self):
        sys.stdout.write(self.CLEAR + self.HIDE)
        w = self._cols()
        border = self.PURPLE + "─" * w + self.RESET
        print(border)
        print()
        for i, line in enumerate(self.BANNER):
            color = self.GRADIENT[i % len(self.GRADIENT)]
            print(self._center(f"{color}{self.BOLD}{line}{self.RESET}", w))
        print()
        tagline = f"{self.DIM}{self.VIOLET}  ▸ Raw Alt Checker{self.RESET}"
        print(self._center(tagline, w))
        credit = f"{self.DIM}{self.PURPLE}  Made by rawnet{self.RESET}"
        print(self._center(credit, w))
        print()
        print(border)
        print()

    def _draw_bar(self, label, current, total, extra=""):
        pct = current / total if total else 1
        w = self._cols()
        bar_w = max(20, w - 42)
        filled = int(bar_w * pct)
        remaining = bar_w - filled

        bar = ""
        for j in range(filled):
            ci = int(j / bar_w * (len(self.GRADIENT) - 1))
            bar += self.GRADIENT[ci] + "█"
        if remaining > 0 and filled > 0:
            bar += self.DIM + "░" + self.RESET
            remaining -= 1
        bar += self.DIM + " " * remaining + self.RESET

        spinner = self.SPINNER_FRAMES[int(time.time() * 10) % len(self.SPINNER_FRAMES)]
        pct_str = f"{pct * 100:5.1f}%"

        line = (
            f"\r  {self.PINK}{spinner}{self.RESET} "
            f"{self.WHITE}{label:<22}{self.RESET} "
            f"{self.DIM}│{self.RESET}{bar}{self.DIM}│{self.RESET} "
            f"{self.CYAN_C}{pct_str}{self.RESET}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def _clear_line(self):
        sys.stdout.write("\r" + " " * self._cols() + "\r")
        sys.stdout.flush()

    def run(self):
        self.silent = True

        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

        self._print_banner()

        sys.stdout.write(self.SHOW)

        webhook_url = input(f"  {self.VIOLET}▸ Webhook URL:{self.RESET} ").strip()
        sys.stdout.write(self.HIDE)
        self._print_banner()

        checks_list = [
            (self.check_official_minecraft, "Minecraft Launcher"),
            (self.check_tlauncher, "TLauncher"),
            (self.check_multimc, "MultiMC/PolyMC"),
            (self.check_lunar_client, "Lunar Client"),
            (self.check_badlion, "Badlion Client"),
            (self.check_feather, "Feather Client"),
            (self.check_labymod, "LabyMod"),
            (self.check_curseforge, "CurseForge"),
            (self.check_atlauncher, "ATLauncher"),
            (self.check_technic, "Technic Launcher"),
            (self.check_modrinth, "Modrinth App"),
            (self.check_logs, "Minecraft Logs"),
            (self.deep_search, "Deep Search"),
        ]

        total = len(checks_list)
        for i, (check_func, check_name) in enumerate(checks_list):
            self._draw_bar(check_name, i, total)
            check_func()
            self._draw_bar(check_name, i + 1, total)

        self._clear_line()

        if self.found_accounts:
            self.fetch_uuids()
            self._clear_line()
            self.send_to_discord(webhook_url)

        self._clear_line()
        done_msg = f"{self.BOLD}{self.CYAN_C}✔  Done{self.RESET}"
        sys.stdout.write(f"\r  {done_msg}")
        time.sleep(1.5)
        sys.stdout.write(self.CLEAR + self.SHOW)


if __name__ == "__main__":
    checker = MinecraftAltChecker()
    try:
        checker.run()
    except KeyboardInterrupt:
        sys.stdout.write(checker.SHOW + checker.RESET)
