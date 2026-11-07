from flask import Flask, jsonify
import aiohttp
import asyncio
import json
from byte import encrypt_api, Encrypt_ID
from visit_count_pb2 import Info

app = Flask(__name__)

ALL_REGIONS = ["BD", "ID", "IND", "BR", "US", "SAC", "NA"]
TARGET_SUCCESS = 1000


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

        return [item["token"] for item in data if "token" in item and item["token"] not in ["", "N/A"]]
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
        "ReleaseVersion": "OB55",
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


async def send_until_target(tokens, uid, server_name, target_success=TARGET_SUCCESS):
    url = get_url(server_name)
    connector = aiohttp.TCPConnector(limit=100)
    total_success = 0
    total_sent = 0
    player_info = None
    token_count = len(tokens)

    async with aiohttp.ClientSession(connector=connector) as session:
        encrypted = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted)

        while total_success < target_success:
            remaining = target_success - total_success
            batch_size = min(remaining, token_count)

            tasks = [
                visit(session, url, tokens[(total_sent + i) % token_count], uid, data)
                for i in range(batch_size)
            ]
            results = await asyncio.gather(*tasks)

            batch_success = 0
            for success, response in results:
                if success:
                    batch_success += 1
                    if player_info is None and response:
                        player_info = parse_protobuf_response(response)

            total_sent += batch_size
            total_success += batch_success

            print(f"Batch: {batch_size} | Success: {batch_success} | Total: {total_success}/{target_success}")

            if batch_success == 0:
                print("No progress in batch, aborting")
                break

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
            "ReleaseVersion": "OB55",
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
    print(f"\nAuto-detecting region for UID: {uid}")
    region = detect_region(uid)

    if not region:
        return jsonify({"error": "Could not detect region for this UID"}), 400

    print(f"Region detected: {region}")
    tokens = load_tokens(region)

    if not tokens:
        return jsonify({"error": "No valid tokens found"}), 500

    print(f"Sending visits to UID: {uid} | Server: {region} | Tokens: {len(tokens)}")

    total_success, total_sent, player_info = asyncio.run(
        send_until_target(tokens, uid, region, target_success=TARGET_SUCCESS)
    )

    print(f"\nDONE! Total success: {total_success} | Total sent: {total_sent}")

    if player_info:
        response_data = {
            "fail": TARGET_SUCCESS - total_success,
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
