from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
async def hello_api():
    """
    A simple hello endpoint to check if the API is responsive.
    """
    return {"message": "Hello from the API router!"}
