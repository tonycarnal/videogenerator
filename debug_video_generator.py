import os
from dotenv import load_dotenv
import video_generator
import image_utils
import structlog
import google.auth

# This script is for manually debugging the start_video_generation_job function.

# --- Setup ---
load_dotenv()
log = structlog.get_logger()

# --- Configuration ---
TEST_IMAGE_PATH = "images/11.jpg"
DOWNLOAD_PATH = "debug_output/generated_video.mp4"
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_REGION = os.environ.get("GCP_REGION")
GCS_BUCKET = os.environ.get("GCS_BUCKET")

def run_debug_test():
    """
    Reads a test image, prepares it, calls the video generation job,
    polls for completion, and downloads the result.
    """
    log.info("debug_test.start", image_path=TEST_IMAGE_PATH)

    if not all([GCP_PROJECT_ID, GCP_REGION, GCS_BUCKET]):
        log.error("debug_test.missing_env_vars",
                  missing=[v for v in ['GCP_PROJECT_ID', 'GCP_REGION', 'GCS_BUCKET'] if not os.environ.get(v)])
        return

    try:
        # 1. Read and prepare the image
        log.info("debug_test.reading_image")
        with open(TEST_IMAGE_PATH, "rb") as f:
            input_bytes = f.read()

        prepared_image_bytes, _ = image_utils.prepare_image_for_veo(input_bytes)
        log.info("debug_test.image_prepared", size=len(prepared_image_bytes))

        # 2. Start the video generation job
        log.info("debug_test.calling_api")
        operation_name, model_id = video_generator.start_video_generation_job(
            project_id=GCP_PROJECT_ID,
            location=GCP_REGION,
            input_image_bytes=prepared_image_bytes,
            output_gcs_uri_prefix=f"gs://{GCS_BUCKET}"
        )
        log.info("debug_test.job_started", operation_name=operation_name, model_id=model_id)

        # 3. Poll for completion
        log.info("debug_test.polling_start")
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        completed_operation = video_generator.poll_operation(
            operation_name, creds, GCP_PROJECT_ID, GCP_REGION, model_id
        )
        log.info("debug_test.polling_complete")

        if "error" in completed_operation:
            error_message = completed_operation["error"].get("message", "Unknown error")
            raise RuntimeError(f"Video generation failed: {error_message}")

        gcs_uri = completed_operation["response"]["videos"][0]["gcsUri"]
        log.info("debug_test.gcs_uri_retrieved", gcs_uri=gcs_uri)

        # 4. Download the result
        video_generator.download_from_gcs(gcs_uri, DOWNLOAD_PATH)

        print("\n--- Debug Test Successful ---")
        print(f"Video downloaded to: {DOWNLOAD_PATH}")
        print("-----------------------------\n")

    except FileNotFoundError:
        log.error("debug_test.file_not_found", path=TEST_IMAGE_PATH)
        print(f"\nError: Test image not found at '{TEST_IMAGE_PATH}'. Please make sure the file exists.")
    except Exception as e:
        log.error("debug_test.error", error=str(e), exc_info=True)
        print(f"\nAn error occurred during the test: {e}")


if __name__ == "__main__":
    run_debug_test()