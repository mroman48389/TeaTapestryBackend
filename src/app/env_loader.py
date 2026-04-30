from dotenv import load_dotenv

# Load variables from .env into environment. Why this small file?
# Ruff will complain if this line comes before any imports, so by 
# placing it in a file that we import, Ruff will be happy.
load_dotenv()