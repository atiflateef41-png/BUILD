import os
import subprocess
import zipfile
import tempfile
import shutil
from flask import Flask, request, send_file, render_template_string

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head><title>APK Builder</title></head>
<body style="font-family: Arial; padding: 20px;">
    <h2>Upload Project ZIP to Build APK</h2>
    <form action="/build" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".zip" required>
        <button type="submit" style="padding: 10px; background: green; color: white;">Build APK</button>
    </form>
</body>
</html>
"""

@app.route('/')
def home():
    return HTML_FORM

@app.route('/build', methods=['POST'])
def build_apk():
    if 'file' not in request.files:
        return "No file uploaded", 400
        
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "project.zip")
    file.save(zip_path)
    
    extract_dir = os.path.join(temp_dir, "project")
    os.makedirs(extract_dir)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Build
        gradlew_path = os.path.join(extract_dir, "gradlew")
        if os.path.exists(gradlew_path):
            os.chmod(gradlew_path, 0o755)
            cmd = ["./gradlew", "assembleDebug"]
        else:
            cmd = ["gradle", "assembleDebug"]
            
        result = subprocess.run(cmd, cwd=extract_dir, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            return f"<h3>Build Failed</h3><pre>{result.stderr}</pre>", 500
            
        apk_path = os.path.join(extract_dir, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
        
        if os.path.exists(apk_path):
            # APK ko temp mein copy karo taaki cleanup ke baad delete na ho
            out_apk = os.path.join(temp_dir, "app-debug.apk")
            shutil.copy(apk_path, out_apk)
            return send_file(out_apk, as_attachment=True, download_name="app-debug.apk")
        else:
            return "<h3>Build Succeeded, but APK not found.</h3>", 500
            
    except Exception as e:
        return f"<h3>Error:</h3><pre>{str(e)}</pre>", 500
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
