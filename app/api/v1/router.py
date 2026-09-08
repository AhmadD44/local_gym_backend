from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    chat,
    classes,
    dashboard,
    exercises,
    gym_info,
    members,
    memberships,
    notifications,
    nutrition,
    progress,
    promotions,
    store,
    trainers,
    water,
    workouts,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(members.router)
api_router.include_router(trainers.router)
api_router.include_router(admin.router)
api_router.include_router(memberships.router)
api_router.include_router(exercises.router)
api_router.include_router(workouts.router)
api_router.include_router(progress.router)
api_router.include_router(classes.router)
api_router.include_router(chat.router)
api_router.include_router(notifications.router)
api_router.include_router(water.router)
api_router.include_router(nutrition.router)
api_router.include_router(store.router)
api_router.include_router(promotions.router)
api_router.include_router(gym_info.router)
api_router.include_router(dashboard.router)
