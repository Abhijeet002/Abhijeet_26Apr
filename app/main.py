from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Store Monitoring System is running!"}
