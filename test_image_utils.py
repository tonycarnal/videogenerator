import unittest
import os
import shutil
import io
import sys
from PIL import Image
from dotenv import load_dotenv
import google.auth

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from image_utils import resize_to_16_9, resize_to_16_9_bytes, prepare_image_for_veo
import video_generator

# Load environment variables for integration tests
load_dotenv()

# --- Unit Tests for Image Utilities ---

class TestImageResizing(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_test_images"
        os.makedirs(self.test_dir, exist_ok=True)
        self.wide_img_path = os.path.join(self.test_dir, "wide.png")
        self.tall_img_path = os.path.join(self.test_dir, "tall.png")
        self.exact_img_path = os.path.join(self.test_dir, "exact.png")
        Image.new('RGB', (200, 90), color='red').save(self.wide_img_path)
        Image.new('RGB', (120, 90), color='blue').save(self.tall_img_path)
        Image.new('RGB', (160, 90), color='green').save(self.exact_img_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_resize_wide_image(self):
        output_path = os.path.join(self.test_dir, "wide_resized.png")
        resize_to_16_9(self.wide_img_path, output_path)
        with Image.open(output_path) as img:
            self.assertEqual(img.size, (200, 112))

    def test_resize_tall_image(self):
        output_path = os.path.join(self.test_dir, "tall_resized.png")
        resize_to_16_9(self.tall_img_path, output_path)
        with Image.open(output_path) as img:
            self.assertEqual(img.size, (160, 90))

class TestPrepareImageForVeo(unittest.TestCase):
    def create_test_image_bytes(self, size, color):
        img = Image.new('RGB', size, color=color)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def test_prepare_image_needs_upscaling(self):
        input_bytes = self.create_test_image_bytes((640, 360), 'yellow')
        # We expect a 16:9 output by default
        prepared_bytes, _, aspect_ratio_str = prepare_image_for_veo(input_bytes)
        with Image.open(io.BytesIO(prepared_bytes)) as img:
            self.assertEqual(img.size, (1280, 720))
            self.assertEqual(aspect_ratio_str, "16:9")

# --- Integration Test for Video Generation ---

# Condition to skip the test if the flag is not set to 'True'
run_integration_tests = os.environ.get("RUN_INTEGRATION_TESTS", "False").lower() == "true"

@unittest.skipIf(not run_integration_tests, "Skipping integration tests. Set RUN_INTEGRATION_TESTS=True to run.")
class TestVideoGenerationIntegration(unittest.TestCase):
    
    def setUp(self):
        self.gcp_project_id = os.environ.get("GCP_PROJECT_ID")
        self.gcp_region = os.environ.get("GCP_REGION")
        self.gcs_bucket = os.environ.get("GCS_BUCKET")
        self.test_image_path = "images/11.jpg"
        self.output_dir = "debug_output"
        os.makedirs(self.output_dir, exist_ok=True)

        if not all([self.gcp_project_id, self.gcp_region, self.gcs_bucket]):
            self.fail("Missing required GCP environment variables for integration test.")

    def test_full_video_generation_and_download(self):
        """
        Tests the full video generation pipeline: start, poll, and download.
        """
        # 1. Prepare the image
        with open(self.test_image_path, "rb") as f:
            input_bytes = f.read()
        # Integration test uses default model (veo3), which should be 16:9
        prepared_image_bytes, _, aspect_ratio_str = prepare_image_for_veo(input_bytes)
        self.assertEqual(aspect_ratio_str, "16:9")

        # 2. Start the video generation job
        operation_name, model_id = video_generator.start_video_generation_job(
            project_id=self.gcp_project_id,
            location=self.gcp_region,
            input_image_bytes=prepared_image_bytes,
            output_gcs_uri_prefix=f"gs://{self.gcs_bucket}"
        )
        self.assertIsNotNone(operation_name)
        self.assertIsNotNone(model_id)

        # 3. Poll for completion
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        completed_operation = video_generator.poll_operation(
            operation_name, creds, self.gcp_project_id, self.gcp_region, model_id
        )
        self.assertNotIn("error", completed_operation)
        self.assertTrue(completed_operation.get("done"))

        # 4. Download the result
        gcs_uri = completed_operation["response"]["videos"][0]["gcsUri"]
        download_path = os.path.join(self.output_dir, "integration_test_video.mp4")
        video_generator.download_from_gcs(gcs_uri, download_path)
        
        self.assertTrue(os.path.exists(download_path))
        self.assertGreater(os.path.getsize(download_path), 0)

if __name__ == '__main__':
    unittest.main()
