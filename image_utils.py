from PIL import Image

def resize_to_16_9(input_path: str, output_path: str):
    """
    Resizes an image to a 16:9 aspect ratio by adding black bars.

    Args:
        input_path: The path to the input image.
        output_path: The path to save the resized image.
    """
    try:
        img = Image.open(input_path)
        width, height = img.size
        target_ratio = 16.0 / 9.0
        img_ratio = float(width) / float(height)

        if abs(img_ratio - target_ratio) < 1e-5:
            # Image is already 16:9 (or very close)
            img.save(output_path)
            return

        if img_ratio > target_ratio:
            # Image is wider than 16:9, add black bars top/bottom
            new_width = width
            new_height = int(width / target_ratio)
            y_offset = (new_height - height) // 2
            x_offset = 0
        else: # img_ratio < target_ratio
            # Image is taller than 16:9, add black bars left/right
            new_width = int(height * target_ratio)
            new_height = height
            x_offset = (new_width - width) // 2
            y_offset = 0

        background = Image.new('RGB', (new_width, new_height), (255, 0, 255))
        background.paste(img, (x_offset, y_offset))
        background.save(output_path)

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


import io

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
        # Ensure image is in RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        target_ratio = 16.0 / 9.0
        img_ratio = float(width) / float(height)

        if abs(img_ratio - target_ratio) < 1e-5:
            return input_bytes

        if img_ratio > target_ratio:
            new_width = width
            new_height = int(width / target_ratio)
            y_offset = (new_height - height) // 2
            x_offset = 0
        else:
            new_width = int(height * target_ratio)
            new_height = height
            x_offset = (new_width - width) // 2
            y_offset = 0

        background = Image.new('RGB', (new_width, new_height), (255, 0, 255))
        background.paste(img, (x_offset, y_offset))

        output_buffer = io.BytesIO()
        img_format = img.format if img.format in ['JPEG', 'PNG'] else 'PNG'
        background.save(output_buffer, format=img_format)
        return output_buffer.getvalue()

    except Exception as e:
        print(f"An error occurred during image resizing: {e}")
        raise


def prepare_image_for_veo(input_bytes: bytes) -> tuple[bytes, float]:
    """
    Prepares an image for the Veo API.
    1. Records original aspect ratio.
    2. Resizes to 16:9 with black bars.
    3. Ensures the output resolution is at least 1280x720.

    Returns:
        A tuple of (prepared_image_bytes, original_aspect_ratio).
    """
    img = Image.open(io.BytesIO(input_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # 1. Record original aspect ratio
    original_width, original_height = img.size
    original_aspect_ratio = original_width / original_height

    # 2. Resize to 16:9
    target_ratio = 16.0 / 9.0

    if abs(original_aspect_ratio - target_ratio) < 1e-5:
        resized_16_9_img = img
    else:
        if original_aspect_ratio > target_ratio:
            new_width = original_width
            new_height = int(new_width / target_ratio)
            background = Image.new('RGB', (new_width, new_height), (255, 0, 255))
            background.paste(img, (0, (new_height - original_height) // 2))
        else: # original_aspect_ratio < target_ratio
            new_height = original_height
            new_width = int(new_height * target_ratio)
            background = Image.new('RGB', (new_width, new_height), (255, 0, 255))
            background.paste(img, ((new_width - original_width) // 2, 0))
        resized_16_9_img = background

    # 3. Ensure resolution is at least 1280x720
    min_width = 1280
    min_height = 720

    current_width, current_height = resized_16_9_img.size

    if original_width < min_width or original_height < min_height:
        print(f"Upscaling image from {current_width}x{current_height} to meet 720p requirement.")
        final_img = resized_16_9_img.resize((min_width, min_height), Image.Resampling.LANCZOS)
    else:
        final_img = resized_16_9_img

    # Convert to bytes
    output_buffer = io.BytesIO()
    final_img.save(output_buffer, format='PNG')

    return output_buffer.getvalue(), original_aspect_ratio
