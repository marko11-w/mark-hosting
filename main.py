from flask import Flask, send_file

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return send_file("index.html", mimetype="text/html")

@app.route("/health", methods=["GET"])
def health():
    return "✅ Working", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
