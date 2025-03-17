import os
import base64
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
    data = request.json
    image_base64 = data.get("image")

    if not image_base64:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    try:
        # base64デコード
        image_bytes = base64.b64decode(image_base64)

        # Gemini APIで感情分析
        model = genai.GenerativeModel('gemini-pro-vision')
        prompt = "この画像の感情を分析し、'嬉しい', '笑顔', '真顔', '泣き顔' のいずれかに分類してください。"
        response = model.generate_content([prompt, image_bytes])

        # 分類結果の抽出
        category = extract_category(response.text)

        if category:
            # 画像を分類フォルダに保存（ここではファイルシステムへの保存は省略）
            # save_image(image_bytes, category)
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

# def save_image(image_bytes, category):
#     """画像を分類フォルダに保存する（実装例）"""
#     os.makedirs(category, exist_ok=True)
#     filename = f"{len(os.listdir(category)) + 1}.jpg" #ファイル名を連番にする例
#     with open(os.path.join(category, filename), 'wb') as f:
#         f.write(image_bytes)

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"status": "error", "message": "Invalid image format"}), 400

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"status": "error", "message": "Gemini API error"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Image not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)