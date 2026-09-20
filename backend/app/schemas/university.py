from typing import Optional, List
from pydantic import BaseModel

class ModuleBase(BaseModel):
    code: str
    title: str
    term: str = "Autumn 2026"
    credits: int = 15
    color: str = "#10b981"
    description: str = ""

class ModuleCreate(ModuleBase):
    pass

class ModuleResponse(ModuleBase):
    id: int
    created_at: Optional[str] = None
    deadline_count: int = 0
    pending_deadlines: int = 0

class DeadlineBase(BaseModel):
    module_id: int
    title: str
    due_date: str # ISO string or YYYY-MM-DD
    weight_percentage: float = 0.0
    status: str = "pending" # pending, submitted, graded
    grade: Optional[float] = None
    priority: str = "Medium" # Low, Medium, High
    resource_link: str = ""

class DeadlineCreate(DeadlineBase):
    pass

class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    module_id: Optional[int] = None
    due_date: Optional[str] = None
    weight_percentage: Optional[float] = None
    status: Optional[str] = None
    grade: Optional[float] = None
    priority: Optional[str] = None
    resource_link: Optional[str] = None

class DeadlineResponse(DeadlineBase):
    id: int
    module_code: Optional[str] = None
    module_title: Optional[str] = None
    module_color: Optional[str] = "#10b981"
    created_at: Optional[str] = None

class AcademicTaskBase(BaseModel):
    title: str
    module_id: Optional[int] = None
    deadline_id: Optional[int] = None
    status: str = "todo" # todo, in_progress, done
    priority: str = "medium" # low, medium, high
    due_date: Optional[str] = None

class AcademicTaskCreate(AcademicTaskBase):
    pass

class AcademicTaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    module_id: Optional[int] = None
    deadline_id: Optional[int] = None

class AcademicTaskResponse(AcademicTaskBase):
    id: int
    module_code: Optional[str] = None
    deadline_title: Optional[str] = None
    created_at: Optional[str] = None
