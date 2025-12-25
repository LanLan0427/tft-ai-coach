import requests
import google.generativeai as genai
import json

# ================= 設定區 =================
# 1. 填入你的 Riot API Key (注意：只有 24小時效期)
RIOT_API_KEY = "RGAPI-你的_RIOT_KEY_貼在這裡"

# 2. 填入你的 Gemini Key
GEMINI_API_KEY = "你的_GEMINI_KEY_貼在這裡"

# 3. 你想查的人 (格式: 名字 # 標籤)
TARGET_NAME = "你的遊戲ID" 
TARGET_TAG = "TW2" # 或是 TW1, 你的標籤
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)

# Riot API 的區域設定 (台灣屬於 asia 區域)
REGION_ROUTING = "asia" 

def get_headers():
    return {
        "X-Riot-Token": RIOT_API_KEY
    }

def get_puuid(game_name, tag_line):
    print(f"🔍 正在搜尋玩家: {game_name}#{tag_line}...")
    # 闖第一關：用 ID 換 PUUID
    url = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    
    resp = requests.get(url, headers=get_headers())
    if resp.status_code == 200:
        return resp.json().get("puuid")
    else:
        print(f"❌ 找不到玩家 (Code {resp.status_code})")
        return None

def get_last_match_id(puuid):
    print("📜 正在獲取對戰紀錄...")
    # 闖第二關：用 PUUID 換 最近一場 Match ID
    # count=1 表示只抓最新一場
    url = f"https://{REGION_ROUTING}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?start=0&count=1"
    
    resp = requests.get(url, headers=get_headers())
    if resp.status_code == 200:
        matches = resp.json()
        if matches:
            return matches[0] # 回傳最新的一場
    return None

def get_match_detail(match_id, target_puuid):
    print(f"📊 正在分析比賽: {match_id}...")
    # 闖第三關：用 Match ID 換詳細資料
    url = f"https://{REGION_ROUTING}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    
    resp = requests.get(url, headers=get_headers())
    if resp.status_code != 200: return None
    
    data = resp.json()
    
    # 在這場比賽的 8 個玩家中，找到「我自己」
    participants = data['info']['participants']
    my_data = None
    for p in participants:
        if p['puuid'] == target_puuid:
            my_data = p
            break
            
    if not my_data: return None
    
    # 整理資料給 AI 看
    placement = my_data['placement'] # 第幾名
    level = my_data['level'] # 等級
    
    # 整理棋子 (Units)
    units_list = []
    for unit in my_data['units']:
        # unit['character_id'] 通常長這樣 "TFT13_Jinx"
        name = unit['character_id'].split("_")[-1] 
        stars = unit['tier'] # 星級
        units_list.append(f"{name}({stars}星)")
        
    # 整理羈絆 (Traits)
    traits_list = []
    for trait in my_data['traits']:
        if trait['tier_current'] > 0: # 只列出有啟動的羈絆
            trait_name = trait['name'].split("_")[-1]
            traits_list.append(f"{trait_name}({trait['tier_current']})")

    # 組合字串
    result = f"""
    玩家：{TARGET_NAME}
    名次：第 {placement} 名
    等級：{level} 等
    最終陣容：{', '.join(units_list)}
    啟動羈絆：{', '.join(traits_list)}
    """
    return result

def get_ai_coach_comment(match_data):
    print("🧠 正在呼叫 Gemini 教練...")
    
    prompt = f"""
    你是個講話超毒舌的《聯盟戰棋 (TFT)》菁英階級教練。
    請根據以下這場比賽的數據，對這位玩家進行點評：
    {match_data}
    
    請包含：
    1. 【戰況總結】：一句話形容這場表現 (如果是第1名就稱讚，第8名就狂噴)。
    2. 【陣容分析】：針對他抓的棋子和羈絆給出毒舌建議 (例如：抓這種沒用的棋子難怪下去)。
    3. 【下場建議】：給一個好笑的建議。
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    # 1. 拿 PUUID
    puuid = get_puuid(TARGET_NAME, TARGET_TAG)
    
    if puuid:
        # 2. 拿 Match ID
        last_match_id = get_last_match_id(puuid)
        
        if last_match_id:
            # 3. 拿詳細數據
            match_data = get_match_detail(last_match_id, puuid)
            print("\n----- 遊戲數據 -----")
            print(match_data)
            
            # 4. AI 講評
            comment = get_ai_coach_comment(match_data)
            print("\n----- 🤖 毒舌教練講評 -----")
            print(comment)
