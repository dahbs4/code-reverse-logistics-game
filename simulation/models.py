from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class SitePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receiving: int = Field(ge=0, le=250)
    warehouse: int = Field(ge=0, le=250)
    processing: int = Field(ge=0, le=350)
    overtime: float = Field(default=0, ge=0, le=4)
    temporary: int = Field(default=0, ge=0, le=100)
    dispatch: int = Field(ge=0, le=200, description='Maximum trailer releases per day')
    appointments: int = Field(ge=0, le=20, description='Receiving loads per hour')
    hold: bool = False
    expedite: bool = False
    supplemental: int = Field(default=0, ge=0, le=100)
    carrier: Literal['Value Freight', 'National Express'] = 'Value Freight'
    priority: Literal['Oldest first','Mail-In Returns','Store Salvage','DC Salvage'] = 'Oldest first'
    invest: bool = False

class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sites: dict[Literal['IND','EAST'], SitePlan] = Field(default_factory=dict)
    routing: dict[str, Literal['IND','EAST']] = Field(default_factory=dict)
    demand_override: float = Field(default=1, ge=0.5, le=2)

class NewGame(BaseModel):
    scenario: Literal['stable','crisis','peak','breakdown'] = 'stable'
    seed: int = Field(default=42, ge=0, le=2147483647)
    difficulty: Literal['standard','hard'] = 'standard'
    name: str = Field(default='National recovery plan', min_length=1, max_length=80)

class StepRequest(BaseModel):
    hours: Literal[8,24,168] = 24
    action: Action | None = None

class SiteObservation(BaseModel):
    name: str
    inventory: dict[str, int]
    plan: SitePlan
    capacity: dict[str, int]
    yard_capacity: int
    max_workers: int
    upstream_days: float
    yard_days: float
    utilization: float
    equipment: float
    weekly_throughput: dict[str, int]
    processed: int

class Observation(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    name: str
    seed: int
    hour: int = Field(ge=0)
    date: str
    inventory: dict[str, int]
    sites: dict[str, SiteObservation]
    generated: int = Field(ge=0)
    initial: int = Field(ge=0)
    disposed: int = Field(ge=0)
    costs: dict[str, float]
    revenue: float = Field(ge=0)
    score: dict[str, float]
    reward: float
    terminal: dict
