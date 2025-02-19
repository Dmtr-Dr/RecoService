import random
from typing import List

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from service.api.exceptions import AuthorizationError, ModelNotFoundError, UserNotFoundError

from service.api.my_models import (
    als_model,
    autoencoder_model,
    lightfm_model,
    ranker_model,
    recbole_model,
    user_knn_model,
)

from service.log import app_logger


def get_user_knn_recs(user_id: int):
    return user_knn_model(user_id)


def get_als_recs(user_id: int):
    return als_model(user_id)


def get_lightfm_recs(user_id: int):
    return lightfm_model(user_id)


def get_autoencoder_recs(user_id: int):
    return autoencoder_model(user_id)


def get_recbole_recs(user_id: int):
    return recbole_model(user_id)


def get_ranker_recs(user_id: int):
    return ranker_model(user_id)


class RecoResponse(BaseModel):
    user_id: int
    items: List[int]


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin")


@router.get(
    path="/health",
    tags=["Health"],
    responses={
        200: {
            "description": "Health check successful",
            "content": {"application/json": {"example": {"status": "36.6"}}},
        },
        500: {
            "description": "Internal Server Error",
            "content": {"application/json": {"example": {"error": "Internal Server Error"}}},
        },
    },
)
async def health() -> str:
    return "I am alive"


@router.get(
    path="/reco/{model_name}/{user_id}",
    tags=["Recommendations"],
    response_model=RecoResponse,
    responses={
        200: {
            "description": "Success",
            "content": {"application/json": {"example": {"user_id": 1, "items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}},
        },
        401: {"description": "Unauthorized", "content": {"application/json": {"example": {"error": "Unauthorized"}}}},
        404: {"description": "Not Found", "content": {"application/json": {"example": {"error": "Not Found"}}}},
        500: {
            "description": "Internal Server Error",
            "content": {"application/json": {"example": {"error": "Internal Server Error"}}},
        },
    },
)
async def get_reco(
    request: Request,
    model_name: str,
    user_id: int,
    token: str = Depends(oauth2_scheme),
) -> RecoResponse:
    app_logger.info(f"Request for model: {model_name}, user_id: {user_id}")

    if token != "admin":
        raise AuthorizationError(error_message="Authorization failed")

    k_recs = request.app.state.k_recs

    model_functions = {
        "user_knn": get_user_knn_recs(user_id),
        "als": get_als_recs(user_id),
        "lightfm": get_lightfm_recs(user_id),
        "autoencoder_2l_1024_512": get_autoencoder_recs(user_id),
        "RecVAE": get_recbole_recs(user_id),
        "Ranker_lgbm": get_ranker_recs(user_id),
    }

    if user_id > 10**9:
        raise UserNotFoundError(error_message=f"User {user_id} not found")
    if model_name == "top":
        reco = list(range(k_recs))
    elif model_name == "random":
        reco = list(random.sample(range(1001), k_recs))
    elif model_name in model_functions:
        reco = model_functions[model_name]
    else:
        raise ModelNotFoundError(error_message=f"Model {model_name} not found")

    return RecoResponse(user_id=user_id, items=reco)


def add_views(app: FastAPI) -> None:
    app.include_router(router)
