import os
import io
import uuid
from flask import Flask, request, send_file, jsonify
from image_utils import resize_to_16_9_bytes, prepare_image_for_veo
from video_generator import generate_video_from_image, crop_video_to_aspect_ratio, upload_to_gcs_and_get_url
from PIL import Image

app = Flask(__name__)

# Constants from user request
GCP_PROJECT_ID = "nth-canyon-366512"
GCP_REGION = "us-central1"
GCS_BUCKET = "veo3testcarnal"

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

@app.route('/generate-video', methods=['POST'])
def generate_video_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file:
        try:
            input_bytes = file.read()
            original_filename, _ = os.path.splitext(file.filename)

            # 1. Prepare image for Veo
            print("Step 1: Preparing image for Veo API...")
            prepared_image_bytes, original_aspect_ratio = prepare_image_for_veo(input_bytes)
            print("Image preparation complete.")

            # 2. Generate 16:9 video with Veo
            print("Step 2: Calling Veo API to generate video...")
            gcs_uri_16x9 = generate_video_from_image(
                project_id=GCP_PROJECT_ID,
                location=GCP_REGION,
                input_image_bytes=prepared_image_bytes,
                output_gcs_uri_prefix=f"gs://{GCS_BUCKET}"
            )
            print(f"16:9 video generated at: {gcs_uri_16x9}")

            # 3. Crop video back to original aspect ratio
            print("Step 3: Cropping video to original aspect ratio...")
            cropped_video_path = crop_video_to_aspect_ratio(gcs_uri_16x9, original_aspect_ratio)
            print(f"Video cropped and saved to temporary file: {cropped_video_path}")

            # 4. Upload final video to GCS
            print("Step 4: Uploading final cropped video to GCS...")
            destination_blob_name = f"final_videos/{original_filename}_cropped_{uuid.uuid4()}.mp4"
            final_url = upload_to_gcs_and_get_url(
                local_file_path=cropped_video_path,
                gcs_bucket_name=GCS_BUCKET,
                destination_blob_name=destination_blob_name
            )
            print(f"Final video uploaded to: {final_url}")

            return jsonify({"final_video_url": final_url})

        except Exception as e:
            print(f"An error occurred during video generation: {e}")
            # In a real app, you might want more specific error handling and logging
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
