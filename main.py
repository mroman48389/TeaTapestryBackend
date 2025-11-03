# Use FastAPI framework to get decorators like @app.get, routing, validation,
# and docs.
from fastapi import FastAPI

# Create instance of FastAPI. All routes, middleware, and configurations will
# flow through this.
app = FastAPI()

# Define GET endpoint, telling FastAPI to respond to HTTP GET requests at the
# root URL. async "root" function allows us to handle concurrent requests
# efficiently.
#
# To test, make sure you're in the virtual environment (venv) first by doing
#     .\venv\Scripts\Activate.ps1
# in the project directory. Then do
#     python -m uvicorn main:app --reload
# to run the server on port 8000. http://127.0.0.1:8000 will show the message
# we're returning,and http://127.0.0.1:8000/docs will have FastAPI's
# auto-generated Swagger UI to explore and test endpoints. Note that http is
# perfect locally because https requires certificates and encryption that are
# not necessary for local testing. There is no data traveling over the
# internet locally, so there is no risk of interception. 127.0.0.1 is a
# loopback address (localhost), a special IP address that always point to one's
# local machine. You can replace the number in the following URL with
# "localhost".


@app.get("/")
async def root():
    # Return simple message as a JSON response to confirm server is running.
    return {"message": "Tea Tapestry backend is alive!"}

print("This is a very long line that exceeds the 79 character limit and should be flagged.")
