import requests
import json
import time
import hashlib
import os

# ============ KONFIGURASI ============
AKUN_FILE = "akun.txt"
BASE_URL = "https://ff-jwt-gen-api.lovable.app"
TOKEN_FILES = {
    "BD": "token_bd.json",
    "ID": "token_id.json",
    "IND": "token_ind.json",
    "BR": "token_br.json",
    "US": "token_br.json",
    "SAC": "token_br.json",
    "NA": "token_br.json"
}

# ============ BACA AKUN.TXT ============
def load_accounts():
    accounts = []
    if not os.path.exists(AKUN_FILE):
        print(f"[!] File {AKUN_FILE} tidak ditemukan!")
        return accounts
    with open(AKUN_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(':')
            if len(parts) >= 2:
                uid = parts[0].strip()
                pw = parts[1].strip()
                region = parts[2].strip().upper() if len(parts) >= 3 else "ID"
                accounts.append({"uid": uid, "password": pw, "region": region})
    return accounts

# ============ GENERATE TOKEN VIA API ============
def get_token(uid, password):
    # Method 1: GET
    try:
        url = f"{BASE_URL}/api/public/token?guest_uid={uid}&guest_password={password}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token")
            if token:
                return token
    except:
        pass

    # Method 2: POST form
    try:
        url = f"{BASE_URL}/api/public/token"
        resp = requests.post(url, data={"guest_uid": uid, "guest_password": password}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token")
            if token:
                return token
    except:
        pass

    # Method 3: POST JSON
    try:
        resp = requests.post(url, json={"guest_uid": uid, "guest_password": password}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token")
            if token:
                return token
    except:
        pass

    # Method 4: MD5 hash
    try:
        pw_md5 = hashlib.md5(password.encode()).hexdigest()
        url = f"{BASE_URL}/api/public/token?guest_uid={uid}&guest_password={pw_md5}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token")
            if token:
                return token
    except:
        pass

    print(f"[!] Gagal generate token untuk UID: {uid}")
    return None

# ============ SIMPAN TOKEN ============
def save_tokens(region_tokens):
    for region, tokens in region_tokens.items():
        filepath = TOKEN_FILES.get(region, "token_bd.json")
        formatted = [{"token": t["token"]} for t in tokens]
        with open(filepath, 'w') as f:
            json.dump(formatted, f, indent=2)
        print(f"[✓] {len(tokens)} token disimpan ke {filepath}")

# ============ MAIN ============
def refresh_tokens():
    print("[*] Memproses akun...")
    accounts = load_accounts()
    if not accounts:
        print("[!] Tidak ada akun di akun.txt")
        return

    region_tokens = {}
    for acc in accounts:
        uid = acc["uid"]
        pw = acc["password"]
        region = acc["region"]
        print(f"[*] UID: {uid} ({region})...")
        token = get_token(uid, pw)
        if token:
            if region not in region_tokens:
                region_tokens[region] = []
            region_tokens[region].append({
                "uid": uid,
                "token": token
            })
            print(f"    [+] Token: {token[:30]}...")
        else:
            print(f"    [-] Gagal")
        time.sleep(0.5)

    if region_tokens:
        save_tokens(region_tokens)
        print("[✓] Selesai!")
    else:
        print("[!] Tidak ada token yang berhasil.")

if __name__ == "__main__":
    refresh_tokens()
