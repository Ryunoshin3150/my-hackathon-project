import os
import uuid
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, storage, firestore
from datetime import datetime
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

# .envの読み込み
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Flaskアプリの設定
app = Flask(__name__)
CORS(app)

# Firebaseの設定
FIREBASE_CREDENTIALS = "firebase_credentials.json"  # Firebaseの鍵ファイル
FIREBASE_BUCKET = "smilephoto-7fef0.firebasestorage.app"  # Firebase Storageのバケット名

# Firebase 初期化
cred = credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET})
bucket = storage.bucket()
db = firestore.client()  # Firestoreクライアント

# Gemini API 設定
genai.configure(api_key=API_KEY)

# FirestoreのドキュメントID（固定）
DOCUMENT_ID = "12345678910"

# 分類フォルダ
CATEGORIES = ["smile", "funny", "straight", "crying"]

SWAGGER_URL = "/api/docs"
API_URL = "/static/swagger.yml"

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
)

app.register_blueprint(swaggerui_blueprint)

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

def save_album_title(album_id, title):
    """Firestore の `Albums` コレクションにアルバムタイトルを保存"""
    doc_ref = db.collection("Albums").document(DOCUMENT_ID)

    # 既存のデータを取得
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
    else:
        data = {"title": {}}  # タイトルを格納するフィールドを作る

    data["title"][album_id] = title  # 自動生成されたアルバムIDをキーにする
    doc_ref.set(data)  # Firestoreに更新

def save_to_photos(image_url, category, album_id):
    """Firestore の `Photos` コレクションに画像のURLを保存"""
    doc_ref = db.collection("Photos").document(DOCUMENT_ID)

    # 既存のデータを取得（なければ空の辞書）
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
    else:
        data = {"albums": {}}  # albums フィールドを作成

    # アルバムが存在しなければ作成
    album_id = str(album_id)
    if album_id not in data["albums"]:
        data["albums"][album_id] = {category: [] for category in CATEGORIES}

    # 感情カテゴリーごとにURLを追加
    data["albums"][album_id][category].append(image_url)
    doc_ref.set(data)  # Firestoreに更新

@app.route('/upload', methods=['POST'])
def upload_images():
    """イベント ID をキーにして画像を Firestore に保存"""
    if 'title' not in request.form or 'id' not in request.form:
        return jsonify({"status": "error", "message": "title または id が不足"}), 400

    title = request.form['title']
    event_id = request.form['id']  # 受け取ったイベント ID

    # **🔥 アルバムタイトルを Firestore に保存**
    save_album_title(event_id, title)

    if 'images' not in request.files:
        return jsonify({"status": "error", "message": "画像がありません"}), 400

    files = request.files.getlist('images')  # 🔥 複数の画像を受け取る

    try:
        for file in files:
            image_bytes = file.read()

            # **🔥 Gemini API で感情分析**
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "この画像の感情を分析し、'smile', 'funny', 'straight', 'crying' のいずれかに分類し、その中の単語１つのみを返してください（ex. smile）"
            response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])

            category = extract_category(response.text)

            # **🔥 Firebase Storage にアップロード**
            image_url = save_to_firebase_storage(image_bytes, category)

            # **🔥 Firestore にデータを保存（イベント ID ごとに保存）**
            save_to_photos(image_url, category, event_id)

        # 🔥 成功時は `status` のみ返す
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/albums', methods=['GET'])
def get_albums():
    """Firestore からアルバムの一覧を取得し、album_id と album名のセットを返す"""
    try:
        doc_ref = db.collection("Albums").document(DOCUMENT_ID)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            album_titles = data.get("title", {})  # 🔥 Firestore の title フィールドを取得

            # 🔥 album_id と album名 のセットをリスト化
            albums_list = [{"album_id": album_id, "title": title} for album_id, title in album_titles.items()]

            return jsonify({
                "status": "success",
                "albums": albums_list
            })
        else:
            return jsonify({
                "status": "success",
                "albums": []
            })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/images/<album_id>/<category>', methods=['GET'])
def get_images_by_album_and_category(album_id, category):
    """Firestore から指定アルバムの特定の感情の画像一覧を取得"""
    try:
        doc_ref = db.collection("Photos").document(DOCUMENT_ID)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            albums = data.get("albums", {})

            # 指定した `album_id` のデータを取得
            album_data = albums.get(str(album_id), {})

            # 指定カテゴリの画像URLを取得（存在しない場合は空リスト）
            image_urls = album_data.get(category, [])

            return jsonify({
                "status": "success",
                "album_id": album_id,
                "category": category,
                "images": image_urls
            })

        else:
            return jsonify({"status": "error"}), 404  # アルバムが見つからなかった場合

    except Exception:
        return jsonify({"status": "error"}), 500


@app.route('/images/<album_id>/all', methods=['GET'])
def get_all_images_by_album(album_id):
    """Firestore から指定アルバムのすべてのカテゴリの画像を取得"""
    try:
        doc_ref = db.collection("Photos").document(DOCUMENT_ID)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            albums = data.get("albums", {})
            all_images = albums.get(str(album_id), {category: [] for category in CATEGORIES})
        else:
            all_images = {category: [] for category in CATEGORIES}  # デフォルトの空リスト

        return jsonify({"status": "success", "album_id": album_id, "images": all_images})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    return jsonify({'message': 'Hello, world!'})
