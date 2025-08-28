import io
from PIL import Image

def _resize_with_padding(img: Image.Image, target_ratio: float, background_color=(255, 0, 255)) -> Image.Image:
    """
    Resizes a PIL image to a target aspect ratio by adding padding.

    Args:
        img: The input PIL image.
        target_ratio: The target aspect ratio (width / height).
        background_color: The color of the padding.

    Returns:
        The resized PIL image.
    """
    width, height = img.size
    img_ratio = float(width) / float(height)

    if abs(img_ratio - target_ratio) < 1e-5:
        return img

    if img_ratio > target_ratio:
        # Image is wider than target, add padding top/bottom
        new_width = width
        new_height = int(width / target_ratio)
        y_offset = (new_height - height) // 2
        x_offset = 0
    else:  # img_ratio < target_ratio
        # Image is taller than target, add padding left/right
        new_width = int(height * target_ratio)
        new_height = height
        x_offset = (new_width - width) // 2
        y_offset = 0

    background = Image.new('RGB', (new_width, new_height), background_color)
    background.paste(img, (x_offset, y_offset))
    return background

def resize_to_16_9(input_path: str, output_path: str):
    """
    Resizes an image to a 16:9 aspect ratio by adding magenta bars.

    Args:
        input_path: The path to the input image.
        output_path: The path to save the resized image.
    """
    try:
        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        resized_img = _resize_with_padding(img, 16.0 / 9.0)
        
        resized_img.save(output_path)

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def resize_to_16_9_bytes(input_bytes: bytes) -> bytes:
    """
    Resizes an image to a 16:9 aspect ratio from bytes.

    Args:
        input_bytes: The input image as bytes.

    Returns:
        The resized image as bytes.
    """
    try:
        img = Image.open(io.BytesIO(input_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        resized_img = _resize_with_padding(img, 16.0 / 9.0)

        if resized_img is img: # No change was made
            return input_bytes

        output_buffer = io.BytesIO()
        # Preserve original format if it's a common web format, otherwise default to PNG
        img_format = img.format if img.format in ['JPEG', 'PNG'] else 'PNG'
        resized_img.save(output_buffer, format=img_format)
        return output_buffer.getvalue()

    except Exception as e:
        print(f"An error occurred during image resizing: {e}")
        raise

def prepare_image_for_veo(input_bytes: bytes) -> tuple[bytes, float]:
    """
    Prepares an image for the Veo API.
    1. Records original aspect ratio.
    2. Resizes to 16:9 with magenta bars.

    Returns:
        A tuple of (prepared_image_bytes, original_aspect_ratio).
    """
    img = Image.open(io.BytesIO(input_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    original_width, original_height = img.size
    original_aspect_ratio = original_width / original_height

    final_img = _resize_with_padding(img, 16.0 / 9.0)

    output_buffer = io.BytesIO()
    final_img.save(output_buffer, format='PNG')
    return output_buffer.getvalue(), original_aspect_ratio

def prepare_image_for_veo2(input_bytes: bytes) -> tuple[bytes, float, str]:
    """
    Prepares an image for the Veo2 API.
    1. Records original aspect ratio.
    2. Determines the closest supported aspect ratio (16:9 or 9:16).
    3. Resizes to the target aspect ratio with fuchsia bars.

    Returns:
        A tuple of (prepared_image_bytes, original_aspect_ratio, target_aspect_ratio_str).
    """
    img = Image.open(io.BytesIO(input_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    original_width, original_height = img.size
    original_aspect_ratio = original_width / original_height

    aspect_ratio_16_9 = 16.0 / 9.0
    aspect_ratio_9_16 = 9.0 / 16.0

    if abs(original_aspect_ratio - aspect_ratio_16_9) < abs(original_aspect_ratio - aspect_ratio_9_16):
        target_ratio = aspect_ratio_16_9
        target_ratio_str = "16:9"
    else:
        target_ratio = aspect_ratio_9_16
        target_ratio_str = "9:16"

    final_img = _resize_with_padding(img, target_ratio)

    output_buffer = io.BytesIO()
    final_img.save(output_buffer, format='PNG')
    return output_buffer.getvalue(), original_aspect_ratio, target_ratio_str
