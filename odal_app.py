import modal
from fastapi_app import app   # tumhari FastAPI app

# Build image with all dependencies
image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")

modal_app = modal.App("techinfy-verity")

@modal_app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return app
