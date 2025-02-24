
import pandas as pd

def load_herbs():
    try:
        return pd.read_csv("herbs.csv", encoding="utf-8")
    except FileNotFoundError:
        print("❌ 無法讀取 herbs.csv，請確認檔案存在！")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        print("❌ herbs.csv 為空")
        return pd.DataFrame()
    except Exception as e:
        print("❌ 無法解析 herbs.csv:", str(e))
        return pd.DataFrame()

def get_suitable_herbs(user_responses):
    """
    根據使用者的回應推薦適合的藥草，回傳 **僅包含藥草名稱，不含劑量等額外資訊**。
    """
    herbs_df = load_herbs()
    matching_herbs = set()

    for index, row in herbs_df.iterrows():
        for key, value in user_responses.items():
            if key in row and str(row[key]) in str(value):
                matching_herbs.update(row["結果"].strip("[]").replace("'", "").split(", "))

    # 只保留藥草名稱，不含克數資訊
    cleaned_herbs = {herb.split()[0] for herb in matching_herbs if herb}

    return list(cleaned_herbs)[:5]  # 只返回最多5種推薦藥草
