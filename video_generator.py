import base64
import time
import uuid
import requests
import tempfile
import os
import structlog
import shutil
import google.auth
import google.auth.transport.requests
from google.cloud import storage
from moviepy.editor import VideoFileClip
from moviepy.video.fx.all import crop

log = structlog.get_logger()

def get_video_info(file_path: str) -> dict:
    """
    Extracts metadata from a video file.
    """
    log.info("get_video_info.start", path=file_path)
    try:
        with VideoFileClip(file_path) as clip:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            width, height = clip.size
            aspect_ratio = width / height
            
            # MoviePy doesn't directly expose the codec, but we can infer it
            # For this project, we know we are encoding to h264.
            codec = "H.264 (libx264)"

            info = {
                "size_mb": f"{file_size_mb:.2f} MB",
                "width": width,
                "height": height,
                "dimensions": f"{width}x{height}",
                "aspect_ratio": f"{aspect_ratio:.2f}:1",
                "codec": codec
            }
            log.info("get_video_info.success", info=info)
            return info
    except Exception as e:
        log.error("get_video_info.error", error=str(e), exc_info=True)
        return {"error": "Could not retrieve video information."}

def poll_operation(operation_name: str, creds, project_id: str, location: str, model_id: str) -> dict:
    """Polls a long-running operation until it's done."""
    log.info("poll_operation.start", operation_name=operation_name)
    
    polling_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_id}:fetchPredictOperation"
    
    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    request_body = {"operationName": operation_name}

    while True:
        log.debug("poll_operation.polling", operation_name=operation_name)
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        headers["Authorization"] = f"Bearer {creds.token}"

        try:
            response = requests.post(polling_url, headers=headers, json=request_body)
            if response.status_code != 200:
                log.error("poll_operation.request_error", status_code=response.status_code, response_text=response.text)
                response.raise_for_status()
            
            op_data = response.json()

        except requests.exceptions.RequestException as e:
            log.error("poll_operation.request_exception", error=str(e), exc_info=True)
            raise

        if op_data.get("done", False):
            log.info("poll_operation.finished", operation_name=operation_name)
            return op_data

        log.info("poll_operation.in_progress", operation_name=operation_name, wait_seconds=20)
        time.sleep(20)

def start_video_generation_job(
    project_id: str,
    location: str,
    input_image_bytes: bytes,
    output_gcs_uri_prefix: str,
    model: str = "veo3",
    resolution: str = "720p",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    prompt: str = "A high-quality, cinematic rotation around the subject. the video format must be kept the same",
) -> tuple[str, str]:
    """
    Starts the video generation job and returns the operation name.
    """
    log.info("start_video_generation_job.start", project_id=project_id, location=location, model=model)
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    model_id = "veo-2.0-generate-001" if model == "veo2" else "veo-3.0-fast-generate-001"

    start_job_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/{location}/publishers/google/models/{model_id}:predictLongRunning"
    )
    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}

    encoded_image = base64.b64encode(input_image_bytes).decode("utf-8")
    job_id = uuid.uuid4()
    full_output_uri = f"{output_gcs_uri_prefix.rstrip('/')}/{job_id}/"
    log.info("start_video_generation_job.details", model_id=model_id, job_id=str(job_id), output_uri=full_output_uri)

    instances = [{"prompt": prompt, "image": {"bytesBase64Encoded": encoded_image, "mimeType": "image/png"}}]

    parameters = {"storageUri": full_output_uri, "sampleCount": 1}
    if model == "veo2":
        parameters["duration"] = duration
        parameters["aspectRatio"] = aspect_ratio
    else:  # veo3
        parameters["resolution"] = resolution
        parameters["generateAudio"] = False

    request_body = {"instances": instances, "parameters": parameters}
    log.info("start_video_generation_job.request_body", body=request_body)

    try:
        response = requests.post(start_job_url, headers=headers, json=request_body)
        response.raise_for_status()
        operation = response.json()
        operation_name = operation["name"]
        log.info("start_video_generation_job.success", operation_name=operation_name)
        return operation_name, model_id
    except requests.exceptions.RequestException as e:
        log.error("start_video_generation_job.request_error", error=str(e), response_text=response.text, exc_info=True)
        raise

def crop_video_to_aspect_ratio(local_video_path: str, original_aspect_ratio: float) -> str:
    """
    Crops a local video file to a target aspect ratio.
    """
    log.info("crop_video.start", local_path=local_video_path, target_aspect_ratio=original_aspect_ratio)
    
    with VideoFileClip(local_video_path) as clip:
        video_width, video_height = clip.size
        video_aspect_ratio = video_width / video_height
        log.info("crop_video.video_loaded", dimensions=f"{video_width}x{video_height}")

        if abs(original_aspect_ratio - video_aspect_ratio) < 1e-5:
            log.info("crop_video.no_crop_needed")
            # Return a copy since the original will be cleaned up
            output_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix="_cropped.mp4")
            shutil.copy(local_video_path, output_temp_file.name)
            return output_temp_file.name

        # Calculate the new dimensions to match the original aspect ratio, maximizing resolution.
        if original_aspect_ratio > video_aspect_ratio:
            # The original image was wider than the 16:9 video. Crop the top and bottom.
            new_width = video_width
            new_height = int(video_width / original_aspect_ratio)
            x1 = 0
            y1 = (video_height - new_height) / 2
        else:
            # The original image was taller than the 16:9 video. Crop the sides.
            new_height = video_height
            new_width = int(video_height * original_aspect_ratio)
            x1 = (video_width - new_width) / 2
            y1 = 0

        log.info("crop_video.cropping", new_dimensions=f"{int(new_width)}x{int(new_height)}")
        cropped_clip = crop(clip, x1=x1, y1=y1, width=new_width, height=new_height)

        output_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix="_cropped.mp4")
        try:
            log.info("crop_video.writing_output", output_path=output_temp_file.name)
            cropped_clip.write_videofile(output_temp_file.name, codec="libx264", audio=False, logger=None)
        finally:
            # Ensure the clip resources are released
            cropped_clip.close()

        return output_temp_file.name

def download_from_gcs(gcs_uri: str, local_destination_path: str):
    """
    Downloads a file from a GCS URI to a local path.
    """
    log.info("download_from_gcs.start", gcs_uri=gcs_uri, destination=local_destination_path)
    storage_client = storage.Client()

    if not gcs_uri.startswith("gs://"):
        log.error("download_from_gcs.invalid_uri", uri=gcs_uri)
        raise ValueError("Invalid GCS URI. Must start with 'gs://'.")
    
    bucket_name, blob_name = gcs_uri[5:].split("/", 1)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.download_to_filename(local_destination_path)
    log.info("download_from_gcs.success", local_path=local_destination_path)


def upload_to_gcs(local_file_path: str, gcs_bucket_name: str, destination_blob_name: str) -> str:
    """
    Uploads a local file to GCS and returns the blob name.
    """
    log.info("upload_to_gcs.start", local_path=local_file_path, bucket=gcs_bucket_name, blob_name=destination_blob_name)
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(local_file_path)
    log.info("upload_to_gcs.file_uploaded")

    os.remove(local_file_path)
    log.info("upload_to_gcs.cleanup", removed_file=local_file_path)

    return destination_blob_name