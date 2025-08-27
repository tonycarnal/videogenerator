import base64
import structlog
from google.cloud import aiplatform
import google.auth

log = structlog.get_logger()

def generate_prompt_for_image(project_id: str, location: str, image_bytes: bytes) -> str:
    """
    Generates a descriptive, cinematic prompt for an image using the Gemini 2.5 Flash model.

    Args:
        project_id: The Google Cloud project ID.
        location: The Google Cloud location (e.g., "us-central1").
        image_bytes: The image content as bytes.

    Returns:
        A string containing the generated prompt.
    """
    log.info("generate_prompt.start", project_id=project_id, location=location, model="gemini-2.5-flash")

    try:
        # Initialize the Vertex AI client
        aiplatform.init(project=project_id, location=location)
        
        # Load the generative model
        from vertexai.generative_models import GenerativeModel, Part
        model = GenerativeModel("gemini-2.5-flash")

        # Prepare the prompt and image for the model
        prompt = (
            "Analyze this image and generate a creative, cinematic prompt for an AI video generation model that will use this image as the stating point. "
            "Focus on the animation you are expecting from the video generator, as well as the camera movement you should have. Be creative and imaginative. "
            "The format of the image must be respected make that clear in the prompt.If there is fushia bars on the image, this must be kept in hte video all along and not altered "
            "Prompt must contain this Sentences at the beginning-> Format of the video must be the same as the Image. Fushia band must stay in the video all along the animation <-"
            "Only output the prompt for the generator and nothing else"
        )
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        
        # Generate the content
        response = model.generate_content([image_part, prompt])
        
        generated_text = response.text
        log.info("generate_prompt.success", generated_text=generated_text)
        return generated_text.strip()

    except Exception as e:
        log.error("generate_prompt.error", error=str(e), exc_info=True)
        # Return a default prompt in case of an error
        return "A beautiful cinematic shot, camera is slowly rotating around the subject."
