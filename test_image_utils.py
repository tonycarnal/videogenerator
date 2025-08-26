import unittest
import os
import shutil
import io
from PIL import Image
from image_utils import resize_to_16_9, resize_to_16_9_bytes

class TestImageResizing(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_images"
        os.makedirs(self.test_dir, exist_ok=True)

        self.wide_img_path = os.path.join(self.test_dir, "wide.png")
        self.tall_img_path = os.path.join(self.test_dir, "tall.png")
        self.exact_img_path = os.path.join(self.test_dir, "exact.png")

        # Create a wide image (e.g., 20:9 > 16:9)
        Image.new('RGB', (200, 90), color='red').save(self.wide_img_path)
        # Create a tall image (e.g., 4:3 < 16:9)
        Image.new('RGB', (120, 90), color='blue').save(self.tall_img_path)
        # Create a 16:9 image
        Image.new('RGB', (160, 90), color='green').save(self.exact_img_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_resize_wide_image(self):
        output_path = os.path.join(self.test_dir, "wide_resized.png")
        resize_to_16_9(self.wide_img_path, output_path)

        with Image.open(output_path) as img:
            width, height = img.size
            # For a 200x90 input (wider than 16:9)
            # New height should be int(200 / (16/9)) = 112
            self.assertEqual(width, 200)
            self.assertEqual(height, 112)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_resize_tall_image(self):
        output_path = os.path.join(self.test_dir, "tall_resized.png")
        resize_to_16_9(self.tall_img_path, output_path)

        with Image.open(output_path) as img:
            width, height = img.size
            # For a 120x90 input (taller than 16:9)
            # New width should be int(90 * (16/9)) = 160
            self.assertEqual(width, 160)
            self.assertEqual(height, 90)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_resize_exact_16_9_image(self):
        output_path = os.path.join(self.test_dir, "exact_resized.png")
        resize_to_16_9(self.exact_img_path, output_path)

        with Image.open(output_path) as img:
            width, height = img.size
            # For a 160x90 input (already 16:9)
            self.assertEqual(width, 160)
            self.assertEqual(height, 90)

    def test_resize_wide_image_bytes(self):
        with open(self.wide_img_path, 'rb') as f:
            input_bytes = f.read()

        output_bytes = resize_to_16_9_bytes(input_bytes)

        with Image.open(io.BytesIO(output_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 112)

    def test_resize_tall_image_bytes(self):
        with open(self.tall_img_path, 'rb') as f:
            input_bytes = f.read()

        output_bytes = resize_to_16_9_bytes(input_bytes)

        with Image.open(io.BytesIO(output_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 160)
            self.assertEqual(height, 90)

    def test_resize_exact_16_9_image_bytes(self):
        with open(self.exact_img_path, 'rb') as f:
            input_bytes = f.read()

        output_bytes = resize_to_16_9_bytes(input_bytes)

        with Image.open(io.BytesIO(output_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 160)
            self.assertEqual(height, 90)


if __name__ == '__main__':
    unittest.main()
