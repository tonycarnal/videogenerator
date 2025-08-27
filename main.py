import base64
import os
import io
import uuid
import structlog
import datetime
import shutil
from flask import Flask, request, jsonify, render_template, url_for, redirect, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from image_utils import resize_to_16_9_bytes, prepare_image_for_veo
from video_generator import (
    start_video_generation_job, 
    poll_operation, 
    crop_video_to_aspect_ratio, 
    upload_to_gcs, 
    download_from_gcs
)
from PIL import Image
import google.auth
from logging_config import setup_logging

# --- Setup ---
setup_logging()
log = structlog.get_logger()
load_dotenv()
app = Flask(__name__)

# --- Configuration ---
TASKS = {}
RESULTS_DIR = "results"
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_REGION = os.environ.get("GCP_REGION")
GCS_BUCKET = os.environ.get("GCS_BUCKET")

@app.route('/resize', methods=['POST'])
def resize_image_endpoint():
    # ... (This function remains the same)
    log.info("resize_image_endpoint.start")
    if 'file' not in request.files:
        log.warn("resize_image_endpoint.no_file")
        return render_template('index.html', error="No file part in the request"), 400

    file = request.files['file']
    if file.filename == '':
        log.warn("resize_image_endpoint.empty_filename")
        return render_template('index.html', error="No file selected for uploading"), 400

    if file:
        try:
            input_bytes = file.read()
            log.info("resize_image_endpoint.file_read", filename=file.filename, size=len(input_bytes))

            try:
                with Image.open(io.BytesIO(input_bytes)) as img:
                    original_format = img.format or 'PNG'
            except Exception:
                original_format = 'PNG'

            output_bytes = resize_to_16_9_bytes(input_bytes)
            log.info("resize_image_endpoint.resize_complete", new_size=len(output_bytes))

            if not os.environ.get("K_SERVICE"):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                original_filename, original_ext = os.path.splitext(file.filename)
                local_filename = f"{original_filename}_16x9_{timestamp}{original_ext}"
                local_filepath = os.path.join(RESULTS_DIR, local_filename)
                with open(local_filepath, "wb") as f:
                    f.write(output_bytes)
                log.info("resize_image_endpoint.saved_locally", path=local_filepath)

            img_base64 = base64.b64encode(output_bytes).decode('utf-8')
            original_img_base64 = base64.b64encode(input_bytes).decode('utf-8')
            
            with Image.open(io.BytesIO(input_bytes)) as img:
                original_width, original_height = img.size

            return render_template('index.html', 
                                 resized_image=img_base64, 
                                 image_format=original_format.lower(),
                                 original_image=original_img_base64,
                                 original_width=original_width,
                                 original_height=original_height)

        except Exception as e:
            log.error("resize_image_endpoint.error", error=str(e), exc_info=True)
            return render_template('index.html', error=f"An error occurred: {str(e)}"), 500

@app.route('/')
def index():
    log.info("index.accessed")
    return render_template('index.html')

@app.route('/generate-video', methods=['POST'])
def generate_video_endpoint():
    # ... (This function remains the same)
    log.info("generate_video.start")
    if 'file' not in request.files:
        log.warn("generate_video.no_file")
        return render_template('index.html', error="No file part in the request"), 400

    file = request.files['file']
    if file.filename == '':
        log.warn("generate_video.empty_filename")
        return render_template('index.html', error="No file selected for uploading"), 400

    if file:
        try:
            input_bytes = file.read()
            original_filename, _ = os.path.splitext(file.filename)
            log.info("generate_video.file_read", filename=original_filename, size=len(input_bytes))

            task_id = str(uuid.uuid4())
            TASKS[task_id] = {
                "status": "preparing",
                "status_message": "Step 1/4: Preparing image for Veo..."
            }
            log.info("generate_video.task_created", task_id=task_id)

            prepared_image_bytes, original_aspect_ratio = prepare_image_for_veo(input_bytes)
            log.info("generate_video.image_prepared", task_id=task_id)

            TASKS[task_id].update({
                "status": "generating",
                "status_message": "Step 2/4: Calling Veo API to generate video..."
            })
            operation_name, model_id = start_video_generation_job(
                project_id=GCP_PROJECT_ID,
                location=GCP_REGION,
                input_image_bytes=prepared_image_bytes,
                output_gcs_uri_prefix=f"gs://{GCS_BUCKET}"
            )
            log.info("generate_video.job_started", task_id=task_id, operation_name=operation_name)

            TASKS[task_id].update({
                "operation_name": operation_name,
                "model_id": model_id,
                "original_aspect_ratio": original_aspect_ratio,
                "original_filename": original_filename,
            })

            return redirect(url_for('video_result', task_id=task_id))

        except Exception as e:
            log.error("generate_video.start_error", error=str(e), exc_info=True)
            return render_template('index.html', error=f"An error occurred: {str(e)}"), 500

@app.route('/video-result/<task_id>')
def video_result(task_id):
    log.info("video_result.accessed", task_id=task_id)
    return render_template('result.html', task_id=task_id)

@app.route('/videos/<filename>')
def serve_video(filename):
    """Serves a video file from the results directory."""
    log.info("serve_video.requested", filename=filename)
    safe_filename = secure_filename(filename)
    return send_from_directory(RESULTS_DIR, safe_filename, as_attachment=False)

@app.route('/status/<task_id>')
def status_endpoint(task_id):
    log.debug("status_endpoint.check", task_id=task_id)
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"status": "failed", "error": "Task not found"}), 404

    if task["status"] not in ["generating", "cropping", "uploading"]:
        return jsonify(task)

    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        completed_operation = poll_operation(
            task["operation_name"], creds, GCP_PROJECT_ID, GCP_REGION, task["model_id"]
        )

        if "error" in completed_operation:
            raise RuntimeError(completed_operation["error"].get("message", "Unknown error in Veo"))
        
        gcs_uri_16x9 = completed_operation["response"]["videos"][0]["gcsUri"]
        log.info("status_endpoint.veo_complete", task_id=task_id, gcs_uri=gcs_uri_16x9)
        
        # --- Download and Save 16:9 Video ---
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename_16x9 = f"{task['original_filename']}_16x9_{timestamp}.mp4"
        local_filepath_16x9 = os.path.join(RESULTS_DIR, local_filename_16x9)
        download_from_gcs(gcs_uri_16x9, local_filepath_16x9)
        # Generate a URL to serve the 16:9 video locally
        video_16_9_url = url_for('serve_video', filename=local_filename_16x9)

        # --- Crop Video ---
        task.update({"status_message": "Step 3/4: Cropping video to original aspect ratio..."})
        # We use the already downloaded local file for cropping
        cropped_video_path = crop_video_to_aspect_ratio(local_filepath_16x9, task["original_aspect_ratio"])

        # --- Save and Upload Final Video ---
        task.update({"status_message": "Step 4/4: Finalizing video..."})
        final_filename = f"{task['original_filename']}_cropped_{timestamp}.mp4"
        final_filepath = os.path.join(RESULTS_DIR, final_filename)
        shutil.move(cropped_video_path, final_filepath)
        log.info("status_endpoint.saved_locally", path=final_filepath)
        
        final_url = url_for('serve_video', filename=final_filename)

        # If on Cloud Run, still upload to GCS
        if os.environ.get("K_SERVICE"):
            destination_blob_name = f"final_videos/{final_filename}"
            upload_to_gcs(final_filepath, GCS_BUCKET, destination_blob_name)
            log.info("status_endpoint.upload_complete", task_id=task_id, blob_name=destination_blob_name)

        task.update({
            "status": "complete",
            "status_message": "Video generation complete!",
            "video_16_9_url": video_16_9_url,
            "final_video_url": final_url
        })
        
        return jsonify(task)

    except Exception as e:
        log.error("status_endpoint.processing_error", task_id=task_id, error=str(e), exc_info=True)
        task["status"] = "failed"
        task["error"] = str(e)
        return jsonify(task)

if __name__ == "__main__":
    log.info("application.startup", host="0.0.0.0", port=os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
