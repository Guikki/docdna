from pathlib import Path


class Settings:
    PROJECT_NAME = "DocDNA"
    PROJECT_SLOGAN = "Inteligência documental baseada em evidências."


    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    APP_DIR = BASE_DIR / "app"

    STORAGE_DIR = BASE_DIR / "storage"

    UPLOADS_DIR = STORAGE_DIR / "uploads"
    REPORTS_DIR = STORAGE_DIR / "reports"
    DATABASE_DIR = STORAGE_DIR / "database"
    TEMP_DIR = STORAGE_DIR / "temp"
    FINGERPRINTS_DIR = STORAGE_DIR / "fingerprints"
    EXTRACTED_DIR = STORAGE_DIR / "extracted"

    FRONTEND_DIR = APP_DIR / "frontend"

    TEMPLATES_DIR = FRONTEND_DIR / "templates"
    STATIC_DIR = FRONTEND_DIR / "static"

    TESSERACT_CMD = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


settings = Settings()