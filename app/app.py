#ここにFlask書いてネ
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

@app.route('/analyze', methods=['POST'])
def analyze_feeling():
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(text)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/')  # このエンドポイントがルートパス（/）に対応
def home():
    return "Welcome to the Feeling Analysis API!"



if __name__ == '__main__':
    app.run(debug=True)

