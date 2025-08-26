import base64
import time
import uuid
import requests
import tempfile
import os

import google.auth
import google.auth.transport.requests
from google.cloud import storage
from moviepy.editor import VideoFileClip
from moviepy.video.fx.all import crop

def poll_operation(operation_name: str, creds, project_id: str, location: str, model_id: str) -> dict:
    """Polls a long-running operation until it's done."""
    polling_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/{location}/publishers/google/models/{model_id}:fetchPredictOperation"
    )

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    request_body = {"name": operation_name}

    while True:
        # Refresh the token in case the polling takes a long time
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        headers["Authorization"] = f"Bearer {creds.token}"

        response = requests.post(polling_url, headers=headers, json=request_body)
        response.raise_for_status()
        op_data = response.json()

        if op_data.get("done", False):
            print("Video generation operation finished.")
            return op_data

        print("Video generation in progress, waiting 20 seconds...")
        time.sleep(20)


def generate_video_from_image(
    project_id: str,
    location: str,
    input_image_bytes: bytes,
    output_gcs_uri_prefix: str,
    prompt: str = "A high-quality, cinematic rotation around the subject. the video format must be kept the same",
) -> str:
    """
    Generates a video from an image using the Veo model via REST API.

    Args:
        project_id: The Google Cloud project ID.
        location: The Google Cloud region.
        input_image_bytes: The input image as bytes.
        output_gcs_uri_prefix: The GCS URI prefix to store the output video.
        prompt: An optional text prompt.

    Returns:
        The GCS URI of the generated video.
    """
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    model_id = "veo-3.0-fast-generate-001"
    start_job_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/{location}/publishers/google/models/{model_id}:predictLongRunning"
    )

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    encoded_image = base64.b64encode(input_image_bytes).decode("utf-8")

    job_id = uuid.uuid4()
    full_output_uri = f"{output_gcs_uri_prefix.rstrip('/')}/{job_id}/"

    instances = [{"prompt": prompt, "image": {"bytesBase64Encoded": encoded_image, "mimeType": "image/png"}}]
    parameters = {"resolution": "720p", "generateAudio": False, "storageUri": full_output_uri, "sampleCount": 1}

    request_body = {"instances": instances, "parameters": parameters}

    response = requests.post(start_job_url, headers=headers, json=request_body)
    response.raise_for_status()
    operation = response.json()
    operation_name = operation["name"]

    print(f"Started video generation operation: {operation_name}")

    completed_operation = poll_operation(operation_name, creds, project_id, location, model_id)

    if "error" in completed_operation:
        error_message = completed_operation["error"].get("message", "Unknown error")
        raise RuntimeError(f"Video generation failed: {error_message}")

    if "response" not in completed_operation:
        raise RuntimeError(f"Video generation operation completed but returned no response. Full response: {completed_operation}")

    video_uri = completed_operation["response"]["videos"][0]["gcsUri"]
    print(f"Video generated successfully at: {video_uri}")

    return video_uri


def crop_video_to_aspect_ratio(gcs_uri: str, original_aspect_ratio: float) -> str:
    """
    Downloads a video from GCS, crops it to a target aspect ratio, and returns the path to the cropped file.

    Args:
        gcs_uri: The GCS URI of the video to download (e.g., "gs://bucket/video.mp4").
        original_aspect_ratio: The target aspect ratio (width / height).

    Returns:
        The local path to the cropped video file.
    """
    storage_client = storage.Client()

    # Parse GCS URI
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI. Must start with 'gs://'.")
    bucket_name, blob_name = gcs_uri[5:].split("/", 1)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Download to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_in:
        print(f"Downloading video from {gcs_uri} to {temp_in.name}")
        blob.download_to_filename(temp_in.name)

        # Load video clip
        clip = VideoFileClip(temp_in.name)

        video_width, video_height = clip.size
        video_aspect_ratio = video_width / video_height

        # Calculate crop dimensions
        if abs(original_aspect_ratio - video_aspect_ratio) < 1e-5:
            print("Video already has the target aspect ratio. No crop needed.")
            clip.close()
            return temp_in.name

        if original_aspect_ratio > video_aspect_ratio:
            # Original is wider than video (e.g., 16:9 vs 4:3), crop top/bottom
            new_height = video_width / original_aspect_ratio
            new_width = video_width
            y1 = (video_height - new_height) / 2
            x1 = 0
        else:
            # Original is taller than video (e.g., 4:3 vs 16:9), crop sides
            new_width = video_height * original_aspect_ratio
            new_height = video_height
            x1 = (video_width - new_width) / 2
            y1 = 0

        print(f"Cropping video to {int(new_width)}x{int(new_height)}")
        cropped_clip = crop(clip, x1=x1, y1=y1, width=new_width, height=new_height)

        # Save cropped video to another temporary file
        output_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix="_cropped.mp4")
        cropped_clip.write_videofile(output_temp_file.name, codec="libx264", audio=False)

        # Close clips to release file handles
        clip.close()
        cropped_clip.close()

        # Clean up the original downloaded file
        os.remove(temp_in.name)

        return output_temp_file.name


def upload_to_gcs_and_get_url(local_file_path: str, gcs_bucket_name: str, destination_blob_name: str) -> str:
    """
    Uploads a local file to GCS and returns its public URL.

    Args:
        local_file_path: The path to the local file to upload.
        gcs_bucket_name: The name of the GCS bucket.
        destination_blob_name: The desired name for the file in GCS.

    Returns:
        The public URL of the uploaded file.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(destination_blob_name)

    print(f"Uploading {local_file_path} to gs://{gcs_bucket_name}/{destination_blob_name}")
    blob.upload_from_filename(local_file_path)

    # Make the blob publicly viewable
    blob.make_public()

    # Clean up the local temporary file
    os.remove(local_file_path)

    return blob.public_url
