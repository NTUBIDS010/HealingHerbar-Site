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
            你是老濟安 AI 顧問「安爺爺」，請根據使用者的健康狀況推薦 1 款茶飲，你的回應只能100字以內，且回應要活潑並熟知草本知識。

            使用者回應：
            {user_responses}

            相關草本：
            {matched_herbs_text}

            老濟安完整茶飲菜單：
            {menu_text}

            **請從菜單中選擇 1 款最適合的茶飲，不可創造新飲品！**

            回應格式：
            「依據你的身心狀況，適合有 ooxx 草本配方的茶飲，因為含有某某某某藥草，另外安爺爺推薦你這款【XXX】本店飲品，價格是 ABC，幫助你放鬆身心～🍵！！ 快來老濟安找安爺爺我一起喝茶，順便來體驗客製化茶飲吧！」
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
            你是老濟安企業的 AI 吉祥物「安爺爺」，你的任務是與顧客對話，推薦茶飲，並解答企業資訊相關問題。
            以下是老濟安企業資訊：
            {business_info}

            該顧客曾經獲得的推薦：
            - 相關草本：{matched_herbs_text}
            - 推薦茶飲：{recommended_drink or "尚未推薦"}

            你需要根據使用者的詢問 **自然地** 回應問題，讓回應有安爺爺的特色，回答應活潑親切，不要過於正式。回答時 **不得創造不存在的企業資訊**，但可以用口語方式說明老濟安的背景、營業時間、地址、FB 連結等資訊。
            """
        }
       #先限制 conversation_history 只保留最後 10 條
        conversation_history = conversation_history[-10:]

        #    把當前用戶訊息加進對話紀錄
        conversation_history.append({"role": "user", "content": user_message})
        messages_for_openai = [system_message] + conversation_history

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_for_openai,
            max_tokens=300
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
    app.run(debug=True)
