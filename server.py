import openai
import os
import json
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from herb_recommendation import get_suitable_herbs
from pymongo import MongoClient
from datetime import datetime  # 加入時間戳記

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Healing Herbar API is running!"

# ✅ 讀取環境變數
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 讀取 menuData.json
with open("menuData.json", "r", encoding="utf-8") as file:
    menu_items = json.load(file)


# ✅ 連接 MongoDB Atlas
client = MongoClient(os.getenv("MONGO_URI"))
db = client["HealingHerbar"]  # 指定資料庫名稱
conversations = db["conversations"]  # 存放對話的 Collection

# ✅ 老濟安企業資訊
business_info = """
店名：老濟安 Healing Herbar
創立：1972年，萬華龍山寺青草巷
簡介：50多年用草經驗，提供茶飲、點心、調酒、沐浴包等草本養生產品。
地址：萬華區西昌街84號, Taipei, Taiwan
電話：02-2314-1878 / 0905-880-126
FB粉專：https://www.facebook.com/HealingHerbar/?locale=zh_TW
營業時間：
- 週一：未營業
- 週二至週六：上午9:00 - 下午6:00
- 週日：未營業
"""

# ✅ 讀取菜單
try:
    with open("menuData.json", "r", encoding="utf-8") as f:
        menu_items = json.load(f)
except Exception as e:
    print("❌ 無法讀取 menuData.json:", str(e))
    menu_items = []

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        user_id = data.get("user_id")
        user_message = data.get("message", "")
        user_responses = data.get("responses", {})
        current_time = datetime.now().isoformat()
        prompt = ""
        # ✅ 確保 user_id 存在
        if not user_id:
            return jsonify({"error": "❌ user_id 未提供"}), 400

        # ✅ 確保 user_message 或 user_responses 至少有一個被填寫
        if not user_message and not user_responses:
            return jsonify({"error": "❌ 未提供有效訊息或問卷回答"}), 400

        # ✅ **只有當使用者真正互動時，才檢查資料庫**
        existing_convo = conversations.find_one({"user_id": user_id}) or {}
        recommended_drink = existing_convo.get("recommended_drink")
        matched_herbs = existing_convo.get("matched_herbs", [])
#先一次性取得並轉換 conversation_history => OpenAI 需要的 role/content 格式
        raw_history = existing_convo.get("conversation", [])
        if not isinstance(raw_history, list):
            raw_history = []
        
        # 只保留有效的對話訊息並做格式轉換
        conversation_history = []
        for msg in raw_history:
            if not isinstance(msg, dict):
                continue
            if "user" in msg:
                conversation_history.append({"role": "user", "content": msg["user"]})
            elif "ai" in msg:
                conversation_history.append({"role": "assistant", "content": msg["ai"]})

        # ✅ 確保 matched_herbs_text 永遠有值
        matched_herbs_text = ", ".join([
            herb.split(" ")[0]  # 只取藥草名稱，不包含克數
            for herb in matched_herbs[:5]
        ]) if matched_herbs else "無推薦草本"

        # ✅ **如果是問卷資料，則先判斷是否已經推薦過**
        if user_responses and not recommended_drink:
            matched_herbs = get_suitable_herbs(user_responses)
            matched_herbs_text = ", ".join([
                herb.split(" ")[0] for herb in matched_herbs[:5]
            ]) if matched_herbs else "無推薦草本"

            # ✅ **從菜單中選擇推薦茶飲**
            menu_text = "\n".join([
                f"- {item['name']}（{item['category']} | {item['price']}）: {item['description']}"
                for item in menu_items
            ])


            prompt = f"""
            你是老濟安 AI 顧問「安爺爺」，請根據使用者的健康狀況推薦 1 款飲品（包括茶飲與酒類飲品），你的回應只能100字以內，且回應要活潑並熟知草本知識，語句後可以請使用者來老濟安找安爺爺我一起喝茶，順便來體驗客製化茶飲吧！。

            使用者回應：
            {user_responses}

            相關草本：
            {matched_herbs_text}

            老濟安完整菜單（包含草本茶與酒類調飲）：
            {menu_text}

            **請從菜單中選擇 1 款最適合的茶飲，不可創造新飲品！如果使用者有提到酒，也可進行推薦，不一定要推薦問卷結果飲品！**
            """

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=300
            )
            recommended_drink = response["choices"][0]["message"]["content"]

            # ✅ 儲存推薦內容到資料庫
            conversations.update_one(
                {"user_id": user_id},
                {"$set": {"recommended_drink": recommended_drink, "matched_herbs": matched_herbs}},
                upsert=True
            )
        #    如果這次沒帶 user_message（代表剛做完問卷），就直接回傳「推薦結果」即可不再執行後面的一般對話邏輯
        if not user_message.strip():
            # 若 recommended_drink 仍是 None，就回傳個預設訊息
            return jsonify({"response": recommended_drink or "目前無可推薦之茶飲", "prompt": prompt})
        
#################################
        system_message = {
            "role": "system",
            "content": f"""
            你是老濟安企業的 AI 吉祥物「安爺爺」，可愛慈祥的長輩且富有藥學與草本知識，你的任務是與顧客對話，進行飲品推薦，並解答企業資訊相關問題。
            你的回答只能依據下列的飲品菜單和品牌資訊以及原先有的草本知識來完成：
            - 古法Traditional系列：青草茶(Mesona Mint Tea)$55/100、苦茶(Bitter Tea)$68/118、菁萃茶(cold brew tea)$100、青草鮮奶茶(Herbal Milk Tea)$68/130、洛神烏梅釀(Roselle Ume Tea)$68/130
            - 果萃Fruit系列：蜂蜜蘆薈飲(Honey Aloe)$68/130、青草西西里(Lemon Herbal Tea)$129有檸檬青草茶跟蜂蜜、鳳梨白鶴冰茶(Pinapple Herbal Tea)$129有鳳梨元氣茶跟龍眼蜜
            - 客製手沖Customize系列：客製手沖草本茶(Customized Healing Tea)$200是會根據顧客評估生活型態分析調整的手沖茶、客製茶包是七天份的$400
            - 茶萃Tea bag系列（價格都是$120）：元氣百倍茶適合夜貓族、神清氣爽茶適合疲憊的上班族、烏蕨苦茶適合火氣大容易燥熱者、崗梅青草茶可以消暑解熱、去油存菁茶適合少動多餐且無肉不歡的外食族、地錦板藍茶適合季節交替時容易受寒者
            - 草醉Cocktail系列：男神(Old fashioned)$300有青草茶威士忌龍眼蜜、女神(Aphrodite)$320有青草茶貝禮詩奶酒龍眼蜜、First Love$280有洛神烏梅伏特加氣泡水跟龍眼蜜
            - 店名：老濟安 Healing Herbar
            - 創立：1972年，萬華龍山寺青草巷
            - 簡介：50多年用草經驗，提供茶飲、點心、調酒、沐浴包等草本養生產品。
            - 地址：萬華區西昌街84號, Taipei, Taiwan
            - 電話：02-2314-1878 / 0905-880-126
            - FB粉專：https://www.facebook.com/HealingHerbar/?locale=zh_TW
            - 營業時間：週一未營業；週二至週六上午9:00 - 下午6:00；週日未營業
            回應都要是繁體中文，如果顧客詢問的飲品項目不在以上列表中，請推薦本老濟安的飲品。
            如果顧客詢問和企業資訊與菜單中的飲品品項無關的問題，請回答：「因為您詢問和老濟安無關的內容，故無法協助您哦！」
            """
        }
       #先限制 conversation_history 只保留最後 2 條
       #conversation_history = conversation_history[-2:]

        #    把當前用戶訊息加進對話紀錄
        #conversation_history.append({"role": "user", "content": user_message})
        messages_for_openai = [
            system_message,
            {"role": "user", "content": user_message}
        ] #+ conversation_history

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=messages_for_openai,
            max_tokens=300,
            temperature=0.7
        )
        

        ai_reply = response["choices"][0]["message"]["content"]
    
        # 把最新對話存回資料庫
        conversations.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "conversation": {
                        "user": user_message,
                        "ai": ai_reply,
                        "timestamp": current_time
                    }
                },
                "$setOnInsert": {"created_at": current_time},
                "$set": {"updated_at": current_time}
            },
            upsert=True
        )

        return jsonify({"response": ai_reply, "prompt": prompt})

    except Exception as e:
        print("❌ 伺服器錯誤：", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)