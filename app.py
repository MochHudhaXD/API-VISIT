from flask import Flask, jsonify
import aiohttp
import asyncio
import json
from byte import encrypt_api, Encrypt_ID
from visit_count_pb2 import Info

app = Flask(__name__)

ALL_REGIONS = ["BD", "ID", "IND", "BR", "US", "SAC", "NA"]

def load_tokens(server_name):
    try:
        if server_name == "IND":
            path = "token_ind.json"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            path = "token_br.json"
        elif server_name == "ID":
            path = "token_id.json"
        else:
            path = "token_bd.json"

        with open(path, "r") as f:
            data = json.load(f)

        tokens = [item["token"] for item in data if "token" in item and item["token"] not in ["", "N/A"]]
        return tokens
    except:
        return []

def get_url(server_name):
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name == "ID":
        return "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
    else:
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

def parse_protobuf_response(response_data):
    try:
        info = Info()
        info.ParseFromString(response_data)
        return {
            "uid": info.AccountInfo.UID,
            "nickname": info.AccountInfo.PlayerNickname,
            "likes": info.AccountInfo.Likes,
            "region": info.AccountInfo.PlayerRegion,
            "level": info.AccountInfo.Levels
        }
    except:
        return None

async def visit(session, url, token, uid, data):
    headers = {
        "ReleaseVersion": "OB54",
        "X-GA": "v1 1",
        "Authorization": f"Bearer {token}",
        "Host": url.replace("https://", "").split("/")[0]
    }
    try:
        async with session.post(url, headers=headers, data=data, ssl=False, timeout=5) as resp:
            if resp.status == 200:
                return True, await resp.read()
            return False, None
    except:
        return False, None

async def send_visits(tokens, uid, server_name):
    url = get_url(server_name)
    connector = aiohttp.TCPConnector(limit=100)
    total_success = 0
    total_sent = 0
    player_info = None

    async with aiohttp.ClientSession(connector=connector) as session:
        encrypted = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted)

        # 🔥 PARALLEL — semua token dikirim bersamaan
        tasks = [visit(session, url, token, uid, data) for token in tokens]
        results = await asyncio.gather(*tasks)

        for success, response in results:
            total_sent += 1
            if success:
                total_success += 1
                if player_info is None and response:
                    player_info = parse_protobuf_response(response)

    return total_success, total_sent, player_info

def detect_region(uid):
    encrypted = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
    for region in ALL_REGIONS:
        tokens = load_tokens(region)
        if not tokens:
            continue
        url = get_url(region)
        headers = {
            "Authorization": f"Bearer {tokens[0]}",
            "ReleaseVersion": "OB54",
            "X-GA": "v1 1"
        }
        try:
            import requests
            resp = requests.post(url, data=bytes.fromhex(encrypted), headers=headers, verify=False, timeout=3)
            if resp.status_code == 200:
                info = Info()
                info.ParseFromString(resp.content)
                if info.AccountInfo.UID > 0:
                    return region
        except:
            continue
    return None

@app.route('/<int:uid>', methods=['GET'])
def send_visits_auto(uid):
    print(f"\n🔍 Auto-detecting region for UID: {uid}")
    region = detect_region(uid)

    if not region:
        return jsonify({"error": "❌ Could not detect region for this UID"}), 400

    print(f"✅ Region detected: {region}")
    tokens = load_tokens(region)

    if not tokens:
        return jsonify({"error": "❌ No valid tokens found"}), 500

    print(f"🚀 Sending visits to UID: {uid} | Server: {region} | Tokens: {len(tokens)}")

    total_success, total_sent, player_info = asyncio.run(send_visits(tokens, uid, region))

    print(f"\n✅ DONE! Total success: {total_success} | Total sent: {total_sent}")

    if player_info:
        response_data = {
            "fail": total_sent - total_success,
            "level": player_info.get("level", 0),
            "likes": player_info.get("likes", 0),
            "nickname": player_info.get("nickname", ""),
            "region": player_info.get("region", ""),
            "success": total_success,
            "uid": player_info.get("uid", 0)
        }
        return jsonify(response_data), 200
    else:
        return jsonify({"error": "Could not decode player information"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5600, debug=True)
