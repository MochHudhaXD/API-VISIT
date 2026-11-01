import requests
import json
import time
import os

# ============ KONFIGURASI ============
AKUN_FILE = "akun.txt"
BASE_URL = "https://jwt-auto.vercel.app"
TOKEN_ENDPOINT = "/token"
TOKEN_FILES = {
    "BD":  "token_bd.json",
    "ID":  "token_id.json",
    "IND": "token_ind.json",
    "BR":  "token_br.json",
    "US":  "token_br.json",
    "SAC": "token_br.json",
    "NA":  "token_br.json",
}

# ============ BACA AKUN.TXT ============
def load_accounts():
    accounts = []
    if not os.path.exists(AKUN_FILE):
        print(f"[!] File {AKUN_FILE} tidak ditemukan!")
        return accounts
    with open(AKUN_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) >= 2:
                uid = parts[0].strip()
                pw = parts[1].strip()
                region = parts[2].strip().upper() if len(parts) >= 3 else "ID"
                accounts.append({"uid": uid, "password": pw, "region": region})
    return accounts

# ============ GENERATE TOKEN VIA API ============
def get_token(uid, password):
    url = f"{BASE_URL}{TOKEN_ENDPOINT}"
    params = {"uid": uid, "password": password}

    # GET /token?uid=UID&password=PASS
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            token = (
                data.get("token")
                or data.get("token_access")
                or data.get("access_token")
                or (data.get("data") or {}).get("token")
            )
            if token:
                return token
            print(f"[!] 200 tanpa field token: {data}")
        else:
            print(f"[!] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[!] Error GET: {e}")

    # Fallback POST form — sebagian deploy baca dari body
    try:
        resp = requests.post(url, data=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            token = (
                data.get("token")
                or data.get("token_access")
                or data.get("access_token")
                or (data.get("data") or {}).get("token")
            )
            if token:
                return token
    except Exception:
        pass

    print(f"[!] Gagal generate token untuk UID: {uid}")
    return None

# ============ SIMPAN TOKEN ============
def save_tokens(region_tokens):
    for region, tokens in region_tokens.items():
        filepath = TOKEN_FILES.get(region, "token_bd.json")
        formatted = [{"token": t["token"]} for t in tokens]
        with open(filepath, "w") as f:
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
            region_tokens.setdefault(region, []).append({"uid": uid, "token": token})
            print(f"    [+] Token: {token[:30]}...")
        else:
            print("    [-] Gagal")
        time.sleep(0.5)

    if region_tokens:
        save_tokens(region_tokens)
        print("[✓] Selesai!")
    else:
        print("[!] Tidak ada token yang berhasil.")

if __name__ == "__main__":
    refresh_tokens()
