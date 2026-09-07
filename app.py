import shutil
import traceback
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
# from fastapi.templating import Jinja2Templates (Removed since we serve static file)

# Import existing conversion scripts directly without altering them
import step_to_glb
import combine_glb_meshes

app = FastAPI()

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any origin (e.g., Vercel)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

BASE_DIR = Path(__file__).parent
STAGING_STEP_DIR = BASE_DIR / "STEP" / "PL" / "Female Wiggins"
STAGING_GLB_DIR = BASE_DIR / "GLB" / "PL" / "Female Wiggins"

@app.get("/", response_class=FileResponse)
async def serve_ui():
    return FileResponse(BASE_DIR / "index.html")

@app.post("/convert")
async def convert_files(
    files: list[UploadFile] = File(...)
):
    
    try:
        # 1. Prepare Staging Directories
        shutil.rmtree(STAGING_STEP_DIR, ignore_errors=True)
        shutil.rmtree(STAGING_GLB_DIR, ignore_errors=True)
        STAGING_STEP_DIR.mkdir(parents=True, exist_ok=True)
        STAGING_GLB_DIR.mkdir(parents=True, exist_ok=True)

        # 2. Save uploaded STEP files into the staging path
        for file in files:
            file_name_lower = file.filename.lower()
            if file_name_lower.endswith('.step') or file_name_lower.endswith('.stp'):
                file_path = STAGING_STEP_DIR / Path(file.filename).name
                with open(file_path, "wb") as f:
                    f.write(await file.read())

        # 3. Execute conversion functions directly in memory
        step_to_glb.batch_convert()
        combine_glb_meshes.run_combine()

        # 4. Zip generated GLB files
        converted_files = list(STAGING_GLB_DIR.glob("*.glb"))
        if not converted_files:
            return JSONResponse(status_code=400, content={"error": "No files were successfully converted."})
        
        zip_path = BASE_DIR / "converted_glbs.zip"
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(STAGING_GLB_DIR))

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="converted_glbs.zip"
        )

    except Exception as e:
        error_details = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Conversion failed:\n{error_details}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)