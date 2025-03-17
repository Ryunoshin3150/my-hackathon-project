import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# .envの読み込み
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
genai.configure(api_key=API_KEY)

# Flaskアプリの設定
app = Flask(__name__)

# 分類フォルダ
CATEGORIES = ["嬉しい", "笑顔", "真顔", "泣き顔"]

@app.route('/upload', methods=['POST'])
def upload_image():
    # 画像が送信されているかチェック
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file provided"}), 400

    file = request.files['image']

    # 画像ファイルをバイトデータに変換
    image_bytes = file.read()

    try:
        # Gemini APIで感情分析
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "この画像の感情を分析し、'嬉しい', '笑顔', '真顔', '泣き顔' のいずれかに分類してください。"

        response = model.generate_content(
            [
                prompt,
                {"mime_type": "image/jpeg", "data": image_bytes}  # 画像を渡す
            ]
        )

        # 分類結果の抽出
        category = extract_category(response.text)

        if category:
            return jsonify({"status": "success", "category": category})
        else:
            return jsonify({"status": "error", "message": "Failed to categorize image"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def extract_category(text):
    """Gemini APIの応答からカテゴリを抽出する"""
    for category in CATEGORIES:
        if category in text:
            return category
    return None

if __name__ == '__main__':
    app.run(debug=True)
