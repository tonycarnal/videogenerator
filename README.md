# Image Resizing Service

This is a simple web service that resizes images to a 16:9 aspect ratio by adding black bars. The service is built with Flask and is designed to be deployed as a containerized application on Google Cloud Run.

## Features

- Resizes images to a 16:9 aspect ratio.
- Adds black bars to the top/bottom or left/right to fit the aspect ratio without cropping.
- Provides a simple RESTful API endpoint for image resizing.
- Containerized with Docker for easy deployment.
- Includes a Cloud Build pipeline for automated deployment to Google Cloud Run.
- Unit tests to ensure the image resizing logic is correct.

## API Endpoints

### `POST /generate-video`

Upload an image to this endpoint to generate a video based on the image. The service will resize the image to 16:9, generate a video with Veo, and then crop the video back to the original image's aspect ratio.

**Request:**

- Method: `POST`
- URL: `/generate-video`
- Body: `multipart/form-data` with a single file field named `file`.

**Success Response:**

- Code: `200 OK`
- Content: A JSON object with the public URL of the final cropped video.
  ```json
  {
    "final_video_url": "https://storage.googleapis.com/veo3testcarnal/final_videos/my_image_cropped_...mp4"
  }
  ```

**Error Responses:**

- `400 Bad Request`: If no file is provided.
- `500 Internal Server Error`: If any error occurs during the multi-step generation process. The JSON response will contain an error message.

### `POST /resize`

Upload an image to this endpoint to have it resized.

**Request:**

- Method: `POST`
- URL: `/resize`
- Body: `multipart/form-data` with a single file field named `file`.

**Success Response:**

- Code: `200 OK`
- Content: The resized image file. The filename will be appended with `_16x9`.

**Error Responses:**

- `400 Bad Request`: If no file is provided or the file is empty.
- `500 Internal Server Error`: If an error occurs during image processing.

**Example Usage (with cURL):**

```bash
curl -X POST -F "file=@/path/to/your/image.jpg" http://localhost:8080/resize -o resized_image.jpg
```

## Getting Started

### Prerequisites

- Python 3.9+
- Docker
- Google Cloud SDK (for deployment)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. **Install system dependencies (for Pillow):**
   On Debian/Ubuntu:
   ```bash
   sudo apt-get update && sudo apt-get install -y libjpeg-dev zlib1g-dev
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask application:**
   ```bash
   python main.py
   ```
   The application will be available at `http://localhost:8080`.

### Docker Setup

1. **Build the Docker image:**
   ```bash
   docker build -t image-resizer .
   ```

2. **Run the Docker container:**
   ```bash
   docker run -p 8080:8080 image-resizer
   ```
   The application will be available at `http://localhost:8080`.

## Running Tests

To run the unit tests, execute the following command from the root of the project:

```bash
python -m unittest discover tests
```

## Deployment

This project includes a `cloudbuild.yaml` file for automated deployment to Google Cloud Run.

To deploy the service, you will need a Google Cloud project with the Cloud Build, Artifact Registry, and Cloud Run APIs enabled.

1. **Set up your environment variables:**
   ```bash
   export PROJECT_ID="your-gcp-project-id"
   # Optional: Change if you use a different region or service name
   export REGION="us-central1"
   export SERVICE_NAME="image-resize-service"
   ```

2. **Enable the necessary services:**
   ```bash
   gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com run.googleapis.com
   ```

3. **Create an Artifact Registry repository (if you don't have one):**
   ```bash
   gcloud artifacts repositories create cloud-run-source-deploy --repository-format=docker --location=$REGION
   ```

4. **Submit the build to Cloud Build:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml \
     --substitutions=PROJECT_ID=$PROJECT_ID,_DEPLOY_REGION=$REGION,_SERVICE_NAME=$SERVICE_NAME
   ```

This will build the Docker image, push it to Artifact Registry, and deploy it to Cloud Run.

### IAM Permissions

The service account used by the Cloud Run service requires the following IAM roles in your GCP project (`nth-canyon-366512`):

-   `Vertex AI User`: To allow the service to call the Veo model.
-   `Storage Object Admin` on the `veo3testcarnal` bucket: To allow the service to write, read, and manage video files.
