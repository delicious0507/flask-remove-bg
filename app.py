import os
import zipfile
from flask import Flask, render_template, request, send_file
from rembg import remove
from pillow_heif import register_heif_opener
from PIL import Image

# 註冊 HEIC 支援
register_heif_opener()

# 設定 Flask
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
UPLOAD_FOLDER = "static/uploads"
PROCESSED_FOLDER = "static/processed"

# 建立必要的資料夾
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "files" not in request.files:
            return "沒有選擇檔案"

        files = request.files.getlist("files")  # 多檔案上傳
        if len(files) == 0:
            return "未選擇檔案"

        processed_filenames = []

        # 取得使用者選擇的背景顏色
        bg_color = request.form.get("bg_color", "transparent")  # 預設為透明
        if bg_color == "white":
            bg_color = (255, 255, 255, 255)
        elif bg_color == "black":
            bg_color = (0, 0, 0, 255)
        elif bg_color.startswith("#"):  # HEX 顏色
            bg_color = Image.new("RGBA", (1, 1), bg_color).getpixel((0, 0)) + (255,)
        else:
            bg_color = None  # 透明背景

        for file in files:
            if file.filename == "":
                continue  # 跳過空檔案

            try:
                # 讀取圖片並去背
                img = Image.open(file).convert("RGBA")
                output = remove(img)  # 去背處理

                # 如果使用者選擇了背景顏色，則填充背景
                if bg_color:
                    bg_img = Image.new("RGBA", output.size, bg_color)
                    output = Image.alpha_composite(bg_img, output)

                # 取得檔名（不含副檔名）
                filename_base = os.path.splitext(file.filename)[0]

                # 轉換格式（預設 PNG）
                format = request.form.get("format", "PNG").upper()
                if format == "JPG":
                    format = "JPEG"  # Pillow 需要 "JPEG" 而不是 "JPG"

                output_filename = f"{filename_base}_removed.{format.lower()}"
                save_path = os.path.join(PROCESSED_FOLDER, output_filename)

                # **確保背景填充在 JPG / PNG**
                if format in ["JPEG", "JPG"]:
                    output = output.convert("RGB")  # 確保 JPG 沒有透明背景
                elif format == "PNG" and bg_color:  # PNG 但選擇了背景顏色
                    output = output.convert("RGB")

                # 儲存圖片
                output.save(save_path, format)

                processed_filenames.append(output_filename)

            except Exception as e:
                return f"圖片處理錯誤: {str(e)}"

        # 如果只有一個檔案，直接顯示下載連結
        if len(processed_filenames) == 1:
            return render_template("index.html", filenames=processed_filenames)

        # 如果有多個檔案，打包成 ZIP
        zip_filename = "processed_images.zip"
        zip_path = os.path.join(PROCESSED_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for filename in processed_filenames:
                zipf.write(os.path.join(PROCESSED_FOLDER, filename), filename)

        return render_template("index.html", filenames=processed_filenames, zip_filename=zip_filename)

    return render_template("index.html", filenames=None)

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(PROCESSED_FOLDER, filename)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
