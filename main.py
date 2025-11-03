# Use FastAPI framework to get decorators like @app.get, routing, validation, and docs.
from fastapi import FastAPI

# Create instance of FastAPI. All routes, middleware, and configurations will flow through this.
app = FastAPI()

# Define GET endpoint, telling FastAPI to respond to HTTP GET requests at the root URL. async "root"
# function allows us to handle concurrent requests efficiently.
@app.get("/")
async def root():
    # Return simple message as a JSON response to confirm server is running.
    return {"message": "Tea Tapestry backend is alive!"}