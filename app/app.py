import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, storage, firestore
from datetime import datetime
from flask_cors import CORS

# .envの読み込み
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Flaskアプリの設定
app = Flask(__name__)
CORS(app)

# Firebaseの設定
FIREBASE_CREDENTIALS = "firebase_credentials.json"  # Firebaseの鍵ファイル
FIREBASE_BUCKET = "smilephoto-7fef0.firebasestorage.app" # Firebase Storageのバケット名

# Firebase 初期化
cred = credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET})
bucket = storage.bucket()
db = firestore.client()  # Firestoreクライアント

# Gemini API 設定
genai.configure(api_key=API_KEY)

# 分類フォルダ
CATEGORIES = ["smile", "funny", "straight", "crying"]
DOCUMENT_ID = "12345678910"  # Firestore のドキュメントID

def extract_category(text):
    """Gemini APIの応答からカテゴリを抽出する"""
    for category in CATEGORIES:
        if category in text:
            return category
    return "その他"

def save_to_firebase_storage(image_bytes, category):
    """Firebase Storage に画像をアップロードし、URL を取得"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{category}/{timestamp}.jpg"

    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    blob.make_public()

    return blob.public_url

def save_to_firestore(image_url, category):
    """Firestore のドキュメントに画像の URL を追加"""
    doc_ref = db.collection("Photos").document(DOCUMENT_ID)
    
    # 既存のデータを取得（なければ空の辞書）
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
    else:
        data = {}

    # 感情カテゴリーごとにURLを追加
    if category not in data:
        data[category] = []
    
    data[category].append(image_url)
    doc_ref.set(data)  # Firestoreに更新

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file provided"}), 400

    file = request.files['image']
    image_bytes = file.read()

    try:
        # Gemini API で感情分析
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "この画像の感情を分析し、'smile', 'glad', 'straight', 'crying' のいずれかに分類し、その中の単語１つのみを返してください（ex. smile）"
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])

        category = extract_category(response.text)

        # Firebase Storage にアップロード
        image_url = save_to_firebase_storage(image_bytes, category)

        # Firestore にデータを保存
        save_to_firestore(image_url, category)

        return jsonify({"status": "success", "category": category, "image_url": image_url})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/images/<category>', methods=['GET'])
def get_images(category):
    """Firestore から特定の感情の画像一覧を取得"""
    try:
        doc_ref = db.collection("photos").document(DOCUMENT_ID)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            image_urls = data.get(category, [])
        else:
            image_urls = []

        return jsonify({"status": "success", "category": category, "images": image_urls})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    return jsonify({'message': 'Hello, world!'})



