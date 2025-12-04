
import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import the existing auditor class
from trade_check import TradeAuditor

app = FastAPI()

# --- CORS Middleware ---
# Allow requests from the Vue.js development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default port for Vite/Vue
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/audit")
async def run_web_audit(
    current_capital: float = Form(...),
    monthly_start_capital: float = Form(...),
    current_scale: str = Form(...),
    file: UploadFile = File(...)
):
    """
    API endpoint to run the trade audit.
    Accepts system parameters and a transaction file.
    """
    # Create a temporary directory to store the uploaded file
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        # Save the uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Initialize and run the auditor
        auditor = TradeAuditor(
            current_capital=current_capital,
            monthly_start_capital=monthly_start_capital,
            current_scale=current_scale
        )
        report = auditor.run_audit(temp_file_path)
        
        return JSONResponse(content=report)

    except ValueError as e:
        # Handle known exceptions from the auditor (e.g., bad file, wrong scale)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the uploaded file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        # Clean up the directory if it's empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

@app.get("/")
def read_root():
    return {"message": "TradeCheck Audit Backend is running. Use the /api/audit endpoint to post data."}

if __name__ == '__main__':
    # This allows running the server directly for testing
    uvicorn.run(app, host="0.0.0.0", port=8000)
