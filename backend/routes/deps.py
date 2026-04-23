from fastapi import HTTPException, Request, status


def require_auth(request: Request) -> dict:
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user is None:
        auth_error = getattr(request.state, "auth_error", None)
        detail = auth_error or "Missing auth token"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    return {
        "user": auth_user,
        "setting_profile_ids": getattr(request.state, "setting_profile_ids", []),
    }
