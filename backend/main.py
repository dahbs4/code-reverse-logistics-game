import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from simulation.models import WeeklyPlan, NewGame, StepRequest, Observation
from simulation.engine import new_game, observe, SCENARIOS
from simulation.weekly import outlook, commit as commit_weekly, advance_week

class Base(DeclarativeBase): pass
class Game(Base):
    __tablename__='games'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    name: Mapped[str]=mapped_column(String)
    state: Mapped[str]=mapped_column(Text)
    checkpoint: Mapped[str]=mapped_column(Text)
    updated: Mapped[str]=mapped_column(String)

DB=Path(__file__).resolve().parents[1]/'data'
DB.mkdir(exist_ok=True)
engine=create_engine(os.getenv('DATABASE_URL',f'sqlite:///{DB}/games.db'))
Base.metadata.create_all(engine)
Session=sessionmaker(engine)
lock=threading.RLock()
app=FastAPI(title='Reverse Network: Operations Director',version='1.0.0')

def read_game(db,id):
    game=db.get(Game,id)
    if game is None:raise HTTPException(404,'Game not found')
    return game

def result(game,state):return dict(id=game.id,**observe(state))

@app.get('/api/health')
def health():return {'status':'ok'}

@app.get('/api/scenarios')
def scenarios():return SCENARIOS

@app.get('/api/games')
def games():
    with Session() as db:
        return [dict(id=g.id,name=g.name,updated=g.updated,hour=json.loads(g.state)['hour'],scenario=json.loads(g.state)['scenario']['name']) for g in db.query(Game).order_by(Game.updated.desc()).all()]

@app.post('/api/games',response_model=Observation)
def create(req:NewGame):
    state=new_game(**req.model_dump());raw=json.dumps(state)
    with lock,Session.begin() as db:
        game=Game(id=str(uuid.uuid4()),name=req.name,state=raw,checkpoint=raw,updated=datetime.now(timezone.utc).isoformat());db.add(game)
        return result(game,state)

@app.get('/api/games/{id}',response_model=Observation)
def get(id:str):
    with Session() as db:
        game=read_game(db,id);return result(game,json.loads(game.state))

@app.post('/api/games/{id}/preview')
def planning(id:str,action:WeeklyPlan):
    with Session() as db:
        game=read_game(db,id)
        try:return outlook(json.loads(game.state),action.model_dump())
        except ValueError as e:raise HTTPException(422,str(e))

@app.post('/api/games/{id}/action',response_model=Observation)
def commit(id:str,action:WeeklyPlan):
    with lock,Session.begin() as db:
        game=read_game(db,id);s=json.loads(game.state)
        if observe(s)['terminal']['done']:raise HTTPException(409,'Scenario complete; create a new game to continue')
        try:commit_weekly(s,action.model_dump())
        except ValueError as e:raise HTTPException(422,str(e))
        game.state=json.dumps(s);game.updated=datetime.now(timezone.utc).isoformat()
        return result(game,s)

@app.post('/api/games/{id}/step',response_model=Observation)
def step(id:str,req:StepRequest):
    with lock,Session.begin() as db:
        game=read_game(db,id);s=json.loads(game.state)
        try:
            if req.action and observe(s)['terminal']['done']:
                raise HTTPException(409,'Campaign complete; create a new game to continue')
            if req.action:commit_weekly(s,req.action.model_dump())
            advance_week(s)
        except ValueError as e:raise HTTPException(422,str(e))
        game.state=json.dumps(s);game.updated=datetime.now(timezone.utc).isoformat()
        return result(game,s)

@app.post('/api/games/{id}/save')
def save(id:str):
    with lock,Session.begin() as db:
        game=read_game(db,id);game.checkpoint=game.state
        return {'saved':True,'hour':json.loads(game.state)['hour']}

@app.post('/api/games/{id}/restore',response_model=Observation)
def restore(id:str):
    with lock,Session.begin() as db:
        game=read_game(db,id);game.state=game.checkpoint;game.updated=datetime.now(timezone.utc).isoformat()
        return result(game,json.loads(game.state))
