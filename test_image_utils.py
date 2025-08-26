import unittest
import os
import shutil
import io
import sys
from PIL import Image

# Add project root to the Python path to allow importing from the 'image_utils' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from image_utils import resize_to_16_9, resize_to_16_9_bytes

class TestImageResizing(unittest.TestCase):

    def setUp(self):
        self.test_dir = "images"
        os.makedirs(self.test_dir, exist_ok=True)

        self.wide_img_path = os.path.join(self.test_dir, "wide.png")
        self.tall_img_path = os.path.join(self.test_dir, "tall.png")
        self.exact_img_path = os.path.join(self.test_dir, "exact.png")

        # Create a wide image (e.g., 20:9 > 16:9)
        Image.new('RGB', (200, 90), color='red').save(self.wide_img_path)
        # Create a tall image (e.g., 4:3 < 16:9)
        Image.new('RGB', (120, 90), color='blue').save(self.tall_img_path)
        # Create a 16:9 image
        import unittest
import os
import shutil
import io
import sys
from PIL import Image

# Add project root to the Python path to allow importing from the 'image_utils' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from image_utils import resize_to_16_9, resize_to_16_9_bytes, prepare_image_for_veo

class TestImageResizing(unittest.TestCase):

    def setUp(self):
        self.test_dir = "images"
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


class TestPrepareImageForVeo(unittest.TestCase):

    def create_test_image_bytes(self, size, color, img_format='PNG'):
        img = Image.new('RGB', size, color=color)
        buffer = io.BytesIO()
        img.save(buffer, format=img_format)
        return buffer.getvalue()

    def test_prepare_image_already_correct(self):
        # Image is already 16:9 and >= 1280x720
        input_bytes = self.create_test_image_bytes((1920, 1080), 'red')
        original_aspect_ratio = 1920 / 1080

        prepared_bytes, aspect_ratio = prepare_image_for_veo(input_bytes)

        self.assertAlmostEqual(aspect_ratio, original_aspect_ratio, delta=0.01)

        with Image.open(io.BytesIO(prepared_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 1920)
            self.assertEqual(height, 1080)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_prepare_image_needs_letterboxing(self):
        # Image is wider than 16:9 (e.g., 2.35:1)
        input_bytes = self.create_test_image_bytes((1920, 817), 'blue')
        original_aspect_ratio = 1920 / 817

        prepared_bytes, aspect_ratio = prepare_image_for_veo(input_bytes)

        self.assertAlmostEqual(aspect_ratio, original_aspect_ratio, delta=0.01)

        with Image.open(io.BytesIO(prepared_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 1920)
            self.assertEqual(height, 1080) # 1920 / (16/9)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_prepare_image_needs_pillarboxing(self):
        # Image is taller than 16:9 (e.g., 4:3)
        input_bytes = self.create_test_image_bytes((1024, 768), 'green')
        original_aspect_ratio = 1024 / 768

        prepared_bytes, aspect_ratio = prepare_image_for_veo(input_bytes)

        self.assertAlmostEqual(aspect_ratio, original_aspect_ratio, delta=0.01)

        with Image.open(io.BytesIO(prepared_bytes)) as img:
            width, height = img.size
            # Since the original is < 1280 wide, it will be upscaled
            self.assertEqual(width, 1280)
            self.assertEqual(height, 720)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_prepare_image_needs_upscaling(self):
        # Image is 16:9 but smaller than 1280x720
        input_bytes = self.create_test_image_bytes((640, 360), 'yellow')
        original_aspect_ratio = 640 / 360

        prepared_bytes, aspect_ratio = prepare_image_for_veo(input_bytes)

        self.assertAlmostEqual(aspect_ratio, original_aspect_ratio, delta=0.01)

        with Image.open(io.BytesIO(prepared_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 1280)
            self.assertEqual(height, 720)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)

    def test_prepare_image_needs_boxing_and_upscaling(self):
        # Image is not 16:9 and is smaller than 1280x720
        input_bytes = self.create_test_image_bytes((500, 500), 'purple') # 1:1 aspect ratio
        original_aspect_ratio = 1.0

        prepared_bytes, aspect_ratio = prepare_image_for_veo(input_bytes)

        self.assertAlmostEqual(aspect_ratio, original_aspect_ratio, delta=0.01)

        with Image.open(io.BytesIO(prepared_bytes)) as img:
            width, height = img.size
            self.assertEqual(width, 1280)
            self.assertEqual(height, 720)
            self.assertAlmostEqual(width / height, 16/9, delta=0.01)


if __name__ == '__main__':
    unittest.main()


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