import os
import io
from flask import Flask, request, send_file, jsonify
from image_utils import resize_to_16_9_bytes
from PIL import Image

app = Flask(__name__)

@app.route('/resize', methods=['POST'])
def resize_image_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file:
        try:
            input_bytes = file.read()

            # To get original format, we need to open it first
            try:
                with Image.open(io.BytesIO(input_bytes)) as img:
                    original_format = img.format or 'PNG'
            except Exception:
                original_format = 'PNG' # Default if format is not detectable

            output_bytes = resize_to_16_9_bytes(input_bytes)

            output_buffer = io.BytesIO(output_bytes)

            filename, _ = os.path.splitext(file.filename)
            output_filename = f"{filename}_16x9.{original_format.lower()}"

            return send_file(
                output_buffer,
                mimetype=f'image/{original_format.lower()}',
                as_attachment=True,
                download_name=output_filename
            )

        except Exception as e:
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/')
def index():
    return "Image resize service is running. POST an image to /resize.", 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
