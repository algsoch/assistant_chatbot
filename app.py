# Fallback file for deployment compatibility
# This imports the main app from vicky_app.py
from vicky_app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
