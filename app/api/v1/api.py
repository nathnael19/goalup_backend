from fastapi import APIRouter
from app.api.v1.endpoints import (
    tournaments, teams, players, matches, standings, auth, 
    uploads, goals, cards, competitions, substitutions, news, audit_logs
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(players.router, prefix="/players", tags=["players"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(standings.router, prefix="/standings", tags=["standings"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(cards.router, prefix="/cards", tags=["cards"])
api_router.include_router(competitions.router, prefix="/competitions", tags=["competitions"])
api_router.include_router(substitutions.router, prefix="/substitutions", tags=["substitutions"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])

