# Image and Video Generation Service

This is a web service that resizes images and generates videos using Google's Veo model. The service is built with Flask and provides a simple web interface for all its features. It is designed to be deployed as a containerized application on Google Cloud Run.

## Features

-   **Web Interface**: A user-friendly UI for uploading images, previewing them, and triggering resize or video generation jobs.
-   **Image Resizing**: Resizes images to a 16:9 aspect ratio by adding magenta bars (letterboxing/pillarboxing) to avoid impacting the core image content.
-   **Video Generation**:
    -   Uses Google's Veo model to generate a video from an input image, with a choice of 720p or 1080p resolution.
    -   Handles the long-running generation task asynchronously, providing real-time status updates on the UI.
    -   Crops the generated video to match the original image's aspect ratio while preserving the maximum resolution.
-   **Local Development & Video Serving**:
    -   When running locally, all generated images and videos are saved to a `results/` directory.
    -   The Flask server acts as a proxy to securely serve these local video files to the browser, avoiding the need for public buckets.
-   **Structured Logging**: Features a structured logging system (`structlog`) with configurable log levels and file output via a `.env` file.
-   **Deployment**:
    -   Containerized with Docker for easy deployment.
    -   Includes a Cloud Build pipeline for automated deployment to Google Cloud Run.
-   **Testing**: Includes unit tests and a conditional integration test for the full Veo API pipeline.

## Getting Started

### Prerequisites

-   Python 3.9+
-   Docker
-   Google Cloud SDK (for deployment and local authentication)

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a file named `.env` in the root of the project and add the following variables:
    ```
    # GCP Configuration
    GCP_PROJECT_ID="your-gcp-project-id"
    GCP_REGION="your-gcp-region"
    GCS_BUCKET="your-gcs-bucket-name"

    # Logging Configuration
    LOG_LEVEL="INFO"      # (e.g., DEBUG, INFO, WARNING, ERROR)
    LOG_TO_FILE="True"    # (True or False)

    # Set to True to run slow integration tests that call external APIs
    RUN_INTEGRATION_TESTS="False"
    ```

5.  **Authenticate with Google Cloud:**
    For local development, you need to provide application default credentials.
    ```bash
    gcloud auth application-default login
    ```

6.  **Run the Flask application:**
    ```bash
    python main.py
    ```
    The application will be available at `http://localhost:8080`.

## Running Tests

To run the fast unit tests:
```bash
python test_image_utils.py
```

To run the slow integration test that calls the Veo API, first set `RUN_INTEGRATION_TESTS=True` in your `.env` file, and then run the same command.
