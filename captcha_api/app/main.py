from fastapi import FastAPI

app = FastAPI(
    title="Captcha API",
    description="API for captcha generation and verification.",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Captcha API!"}
