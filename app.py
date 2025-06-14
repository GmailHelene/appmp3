from flask import Flask, request, render_template, send_from_directory, redirect, jsonify
import yt_dlp
import os
import zipfile
import time
import random
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import base64

# Last inn environment variabler FØRST
load_dotenv()

# Opprett Flask-appen TIDLIG
app = Flask(__name__)

# Sett SECRET_KEY fra environment variabel
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Hvis SECRET_KEY ikke finnes, generer en midlertidig en
if not app.config['SECRET_KEY']:
    import secrets
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    print("⚠️  WARNING: Using temporary SECRET_KEY. Set SECRET_KEY in .env file!")

# NÅ kan du definere rutene
@app.route('/qr')
def generate_qr():
    try:
        # Generer QR-kode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data('https://helen.cloud/mp3.html')
        qr.make(fit=True)
        
        # Lag bilde
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Konverter til base64 for visning
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>QR-kode</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body style="text-align: center; font-family: Arial, sans-serif; padding: 20px;">
            <h1>QR-kode for helen.cloud/mp3.html</h1>
            <img src="data:image/png;base64,{img_str}" alt="QR Code" style="max-width: 300px;">
            <p>Skann for å gå til helen.cloud/mp3.html</p>
            <a href="/mp3" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Tilbake til app</a>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Feil ved generering av QR-kode: {str(e)}", 500

ZIP_NAME = "alle_sanger.zip"
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# Force HTTPS in production
@app.before_request
def force_https():
    if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        if 'localhost' not in request.host and '127.0.0.1' not in request.host:
            return redirect(request.url.replace('http://', 'https://'))


def get_ydl_opts(safe_title):
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "postprocessor_args": ["-ar", "44100"],
        "prefer_ffmpeg": True,
        "ffmpeg_location": "ffmpeg",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "referer": "https://www.youtube.com/",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
        "age_limit": 18,
        "retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 1,
        "max_sleep_interval": 5,
        "quiet": True,
        "no_warnings": True,
    }

def file_was_downloaded(safe_title, download_folder):
    """Sjekk om filen faktisk ble lastet ned"""
    for file in os.listdir(download_folder):
        if file.startswith(safe_title) and file.endswith('.mp3'):
            return True
    return False

@app.route("/")
def redirect_to_mp3():
    """Videresender til hovedfunksjonaliteten"""
    return redirect("/mp3")

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route("/mp3", methods=["GET", "POST"])
def mp3_downloader():
    status = ""
    files = []
    if request.method == "POST":
        input_text = request.form["songs"]
        song_titles = [line.strip() for line in input_text.strip().split("\n") if line.strip()]

        files_before = set(f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3"))

        for i, title in enumerate(song_titles):
            try:
                if i > 0:
                    time.sleep(random.uniform(2, 5))

                safe_title = title.replace(" ", "_").replace("/", "_").replace(":", "_").replace("?", "").replace("*", "").replace("<", "").replace(">", "").replace("|", "")
                ydl_opts = get_ydl_opts(safe_title)

                download_successful = False

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([f"ytsearch1:{title}"])

                    if file_was_downloaded(safe_title, DOWNLOAD_FOLDER):
                        status += f"✅ {title} - Nedlastet fra YouTube<br>"
                        download_successful = True
                    else:
                        raise Exception("Ingen fil ble opprettet")

                except Exception as youtube_error:
                    if not download_successful:
                        status += f""

                        try:
                            sc_ydl_opts = ydl_opts.copy()
                            with yt_dlp.YoutubeDL(sc_ydl_opts) as ydl:
                                ydl.download([f"scsearch1:{title}"])

                            if file_was_downloaded(safe_title, DOWNLOAD_FOLDER):
                                status += f"✅ {title} - Nedlastet fra SoundCloud<br>"
                                download_successful = True

                        except Exception as sc_error:
                            pass

                if not download_successful:
                    error_msg = str(youtube_error) if 'youtube_error' in locals() else "Ukjent feil"
                    if "Sign in to confirm" in error_msg:
                        status += f"❌ {title} - YouTube krever innlogging. Prøv igjen senere.<br>"
                    else:
                        status += f"❌ {title} <br>"

            except Exception as e:
                status += f"❌ {title} - Uventet feil: {str(e)}<br>"

        files_after = set(f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3"))
        new_files = files_after - files_before

        if new_files:
            status += f"<br><strong>🎉 Totalt {len(new_files)} nye filer lastet ned!</strong><br>"

            zip_path = os.path.join(DOWNLOAD_FOLDER, ZIP_NAME)
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for f in files_after:
                    zipf.write(os.path.join(DOWNLOAD_FOLDER, f), arcname=f)

    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
    return render_template("mp3.html", status=status, files=files)

@app.route("/downloads/<filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route("/download_zip")
def download_zip():
    return send_from_directory(DOWNLOAD_FOLDER, ZIP_NAME, as_attachment=True)

@app.route("/clear")
def clear_downloads():
    try:
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return "Alle filer er slettet!"
    except Exception as e:
        return f"Feil ved sletting: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
