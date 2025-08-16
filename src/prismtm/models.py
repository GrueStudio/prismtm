from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Union
import re

class BugSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BugStatus(Enum):
    OPEN = "open"
    REPRODUCED = "reproduced"
    FOUND = "found"
    FIXED = "fixed"
    CLOSED = "closed"

class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"

class TaskPath:
    """Utility class for parsing and validating task paths."""

    PATH_PATTERN = re.compile(r'^([^/]+)(?:/([^/]+)(?:/([^/]+)(?:/(.+))?)?)?$')
    VERSION_PATTERN = re.compile(r'^\d+\.\d+(?:\.\d+)?(?:\.[x*])?$')

    def __init__(self, path: str):
        self.raw_path = path
        self.phase = None
        self.milestone = None
        self.block = None
        self.task = None
        self._parse()

    def _parse(self):
        """Parse the path into components."""
        match = self.PATH_PATTERN.match(self.raw_path)
        if not match:
            raise ValueError(f"Invalid task path format: {self.raw_path}")

        self.phase = match.group(1)
        self.milestone = match.group(2)
        self.block = match.group(3)
        self.task = match.group(4)

    @classmethod
    def validate_path(cls, path: str) -> bool:
        """Validate if a path string is properly formatted."""
        try:
            cls(path)
            return True
        except ValueError:
            return False

    @classmethod
    def validate_version(cls, version: str) -> bool:
        """Validate if a version string is properly formatted."""
        return bool(cls.VERSION_PATTERN.match(version))

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert path to dictionary representation."""
        return {
            'phase': self.phase,
            'milestone': self.milestone,
            'block': self.block,
            'task': self.task
        }

    def __str__(self) -> str:
        return self.raw_path

class TaskTree(BaseModel):
    """The Full Task Tree for a project."""

    _schema_scope: str = "project"
    _schema_filename: str = "tasks"

    current_task_path: str = Field(description="The taskpath to the currently active task")
    nav_path: str = Field(description="The taskpath to where the user is currently looking at")
    phases: List['TaskTree.Phase'] = Field(
        default_factory=list,
        description="List of project phases"
    )
    orphans: List['TaskTree.Orphan'] = Field(
        default_factory=list,
        description="List of orphan tasks"
    )

    @field_validator('current_task_path', 'nav_path')
    def validate_paths(cls, v):
        if v and not TaskPath.validate_path(v):
            raise ValueError(f"Invalid task path format: {v}")
        return v

    def find_by_path(self, path: str) -> Optional[Union['Phase', 'Milestone', 'Block', 'Task', 'SubTask']]:
        """Find a task tree element by its path."""
        task_path = TaskPath(path)

        # Find phase
        phase = self.find_phase(task_path.phase)
        if not phase or not task_path.milestone:
            return phase

        # Find milestone
        milestone = phase.find_milestone(task_path.milestone)
        if not milestone or not task_path.block:
            return milestone

        # Find block
        block = milestone.find_block(task_path.block)
        if not block or not task_path.task:
            return block

        # Find task
        task = block.find_task(task_path.task)
        return task

    def find_phase(self, name: str) -> Optional['Phase']:
        """Find a phase by name."""
        return next((p for p in self.phases if p.name == name), None)

    def get_completion_suggestions(self, partial_path: str) -> List[str]:
        """Get tab completion suggestions for a partial path."""
        suggestions = []
        parts = partial_path.split('/')

        if len(parts) == 1:
            # Phase completion
            suggestions = [p.name for p in self.phases if p.name.startswith(parts[0])]
        elif len(parts) == 2:
            # Milestone completion
            phase = self.find_phase(parts[0])
            if phase:
                suggestions = [f"{parts[0]}/{m.versions}" for m in phase.milestones
                             if m.versions.startswith(parts[1])]
        elif len(parts) == 3:
            # Block completion
            phase = self.find_phase(parts[0])
            if phase:
                milestone = phase.find_milestone(parts[1])
                if milestone:
                    suggestions = [f"{parts[0]}/{parts[1]}/{b.version}" for b in milestone.blocks
                                 if b.version.startswith(parts[2])]
        elif len(parts) == 4:
            # Task completion
            phase = self.find_phase(parts[0])
            if phase:
                milestone = phase.find_milestone(parts[1])
                if milestone:
                    block = milestone.find_block(parts[2])
                    if block:
                        suggestions = [f"{parts[0]}/{parts[1]}/{parts[2]}/{t.name}"
                                     for t in block.tasks if t.name.startswith(parts[3])]

        return suggestions

    class Phase(BaseModel):
        name: str = Field(description="The human readable identifier of the phase. ie. pre-alpha, alpha, beta, release")
        version_match: str = Field(description="The versions that match the phase such as 0.8+.* or 1.*.*")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the phase")
        started_at: Optional[datetime] = Field(default=None, description="When the phase was started")
        finished_at: Optional[datetime] = Field(default=None, description="When the phase was finished")
        milestones: List['TaskTree.Milestone'] = Field(
            default_factory=list,
            description="List of phase milestones"
        )

        @model_validator(mode='after')
        def validate_dates(self):
            if self.started_at and self.finished_at and self.finished_at < self.started_at:
                raise ValueError("finished_at must be after started_at")
            return self

        def find_milestone(self, versions: str) -> Optional['TaskTree.Milestone']:
            """Find a milestone by versions."""
            return next((m for m in self.milestones if m.versions == versions), None)

    class Milestone(BaseModel):
        versions: str = Field(description="The versions that encompass this milestone; such as 0.1.x, or 3.2.x.")
        reason: str = Field(description="Why do we need this milestone?")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the milestone")
        started_at: Optional[datetime] = Field(default=None, description="When the milestone was started.")
        finished_at: Optional[datetime] = Field(default=None, description="When the milestone was finished.")
        blocks: List['TaskTree.Block'] = Field(
            default_factory=list,
            description="List of milestone blocks"
        )

        @field_validator('versions')
        @classmethod
        def validate_version_format(cls, v):
            if not TaskPath.validate_version(v):
                raise ValueError(f"Invalid version format: {v}")
            return v

        @model_validator(mode='after')
        def validate_dates(self):
            if self.started_at and self.finished_at and self.finished_at < self.started_at:
                raise ValueError("finished_at must be after started_at")
            return self

        def find_block(self, version: str) -> Optional['TaskTree.Block']:
            """Find a block by version."""
            return next((b for b in self.blocks if b.version == version), None)

    class Block(BaseModel):
        version: str = Field(description="The version the block is for; such as 0.1.1 or 3.2.15.")
        reason: str = Field(description="Why do we need this block?")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the block")
        started_at: Optional[datetime] = Field(default=None, description="When the block was started.")
        finished_at: Optional[datetime] = Field(default=None, description="When the block was finished.")
        tasks: List['TaskTree.Task'] = Field(
            default_factory=list,
            description="List of block tasks"
        )

        @field_validator('version')
        @classmethod
        def validate_version_format(cls, v):
            if not TaskPath.validate_version(v):
                raise ValueError(f"Invalid version format: {v}")
            return v

        @model_validator(mode='after')
        def validate_dates(self):
            if self.started_at and self.finished_at and self.finished_at < self.started_at:
                raise ValueError("finished_at must be after started_at")
            return self

        def find_task(self, name: str) -> Optional['TaskTree.Task']:
            """Find a task by name."""
            return next((t for t in self.tasks if t.name == name), None)

    class Task(BaseModel):
        name: str = Field(description="The human readable identifier of the task.")
        reason: str = Field(description="Why do we need this task?")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the task")
        started_at: Optional[datetime] = Field(default=None, description="When the task was started.")
        finished_at: Optional[datetime] = Field(default=None, description="When the task was finished.")
        subtasks: List['TaskTree.SubTask'] = Field(
            default_factory=list,
            description="List of task sub-tasks"
        )

        @model_validator(mode='after')
        def validate_dates(self):
            if self.started_at and self.finished_at and self.finished_at < self.started_at:
                raise ValueError("finished_at must be after started_at")
            return self

        def find_subtask(self, name: str) -> Optional['TaskTree.SubTask']:
            """Find a subtask by name."""
            return next((st for st in self.subtasks if st.name == name), None)

    class SubTask(BaseModel):
        name: str = Field(description="The human readable identifier of the sub-task.")
        reason: str = Field(description="Why do we need this sub-task?")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the sub-task")
        started_at: Optional[datetime] = Field(default=None, description="When the sub-task was started.")
        finished_at: Optional[datetime] = Field(default=None, description="When the sub-task was finished.")

        @model_validator(mode='after')
        def validate_dates(self):
            if self.started_at and self.finished_at and self.finished_at < self.started_at:
                raise ValueError("finished_at must be after started_at")
            return self

    class Orphan(BaseModel):
        id: str = Field(description="Unique identifier for the orphan.")
        name: str = Field(description="The human readable identifier of the orphan.")
        reason: str = Field(description="Why do we need this orphan task?")
        status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the orphan")

TaskTree.model_rebuild()

class ProjectBugList(BaseModel):
    """Tracks all bugs across the project."""

    _schema_scope: str = "project"
    _schema_filename: str = "bugs"

    tags: List[str] = Field(
        default_factory=list,
        description="List of used tags"
    )
    bugs: Dict[str, List['ProjectBugList.Bug']] = Field(
        default_factory=dict,
        description="A map of bugs (value) to their originating project (key)"
    )

    class Bug(BaseModel):
        id: str = Field(description="Unique identifier for the bug")
        title: str = Field(description="Title of the bug")
        version: str = Field(description="Version of the software when the bug was found")
        description: str = Field(description="Detailed description of the bug")
        status: BugStatus = Field(description="Status of the bug")
        priority: str = Field(description="Priority of the bug")
        opened_at: datetime = Field(description="Date and time when the bug was opened")
        reproduced_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was reproduced")
        reproduction_steps: Optional[str] = Field(default=None, description="Steps to reproduce the bug")
        found_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was found")
        reason: Optional[str] = Field(default=None, description="Reason for the bug")
        fixed_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was closed")
        fix_description: Optional[str] = Field(default=None, description="Description of the fix")
        version_fixed: Optional[str] = Field(default=None, description="Version of the software when the bug was fixed")
        tags: List[str] = Field(
            default_factory=list,
            description="List of applicable tags"
        )

        @field_validator('version', 'version_fixed')
        @classmethod
        def validate_version_format(cls, v):
            if v and not TaskPath.validate_version(v):
                raise ValueError(f"Invalid version format: {v}")
            return v

ProjectBugList.model_rebuild()

class GlobalBugList(BaseModel):
    """Tracks all bugs across all projects for a user."""

    _schema_scope: str = "user"
    _schema_filename: str = "bugs"

    tags: List[str] = Field(
        default_factory=list,
        description="List of used tags"
    )
    bugs: Dict[str, List['GlobalBugList.Bug']] = Field(
        default_factory=dict,
        description="A map of bugs (value) to their originating project (key)"
    )

    class Bug(BaseModel):
        id: str = Field(description="Unique identifier for the bug")
        project: str = Field(description="Project where the bug was found")
        title: str = Field(description="Title of the bug")
        version: str = Field(description="Version of the software when the bug was found")
        description: str = Field(description="Detailed description of the bug")
        status: BugStatus = Field(description="Status of the bug")
        priority: str = Field(description="Priority of the bug")
        opened_at: datetime = Field(description="Date and time when the bug was opened")
        reproduced_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was reproduced")
        reproduction_steps: Optional[str] = Field(default=None, description="Steps to reproduce the bug")
        found_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was found")
        reason: Optional[str] = Field(default=None, description="Reason for the bug")
        fixed_at: Optional[datetime] = Field(default=None, description="Date and time when the bug was closed")
        fix_description: Optional[str] = Field(default=None, description="Description of the fix")
        version_fixed: Optional[str] = Field(default=None, description="Version of the software when the bug was fixed")
        tags: List[str] = Field(
            default_factory=list,
            description="List of applicable tags"
        )

        @field_validator('version', 'version_fixed')
        @classmethod
        def validate_version_format(cls, v):
            if v and not TaskPath.validate_version(v):
                raise ValueError(f"Invalid version format: {v}")
            return v

GlobalBugList.model_rebuild()

class SessionType(Enum):
    WORK = "work"
    BREAK = "break"
    PAUSE = "pause"

class ProjectTimeTracker(BaseModel):
    """Project-scoped time tracking system that logs work sessions independently from task tree structure."""

    _schema_scope: str = "project"
    _schema_filename: str = "time"

    current_session: Optional['ProjectTimeTracker.ActiveTimeSession'] = Field(
        default=None,
        description="Currently active time tracking session, null if no session is active"
    )
    sessions: List['ProjectTimeTracker.TimeSession'] = Field(
        default_factory=list,
        description="Historical log of completed time tracking sessions"
    )

    def start_session(self, target_path: str, description: Optional[str] = None) -> 'ActiveTimeSession':
        """Start a new time tracking session."""
        if self.current_session:
            raise ValueError("A session is already active. Stop the current session first.")

        self.current_session = self.ActiveTimeSession(
            started_at=datetime.now(),
            target_path=target_path,
            description=description
        )
        return self.current_session

    def stop_session(self, description: Optional[str] = None, session_type: SessionType = SessionType.WORK) -> 'TimeSession':
        """Stop the current session and add it to the log."""
        if not self.current_session:
            raise ValueError("No active session to stop.")

        ended_at = datetime.now()
        duration = ended_at - self.current_session.started_at

        completed_session = self.TimeSession(
            started_at=self.current_session.started_at,
            ended_at=ended_at,
            target_path=self.current_session.target_path,
            duration=duration,
            description=description or self.current_session.description,
            session_type=session_type
        )

        self.sessions.append(completed_session)
        self.current_session = None
        return completed_session

    def get_total_time_for_path(self, target_path: str) -> timedelta:
        """Get total time spent on a specific path."""
        total = timedelta()
        for session in self.sessions:
            if session.target_path == target_path and session.session_type == SessionType.WORK:
                total += session.duration
        return total

    class ActiveTimeSession(BaseModel):
        started_at: datetime = Field(description="When the current session was started")
        target_path: str = Field(description="The task path this session is targeting")
        description: Optional[str] = Field(default=None, description="Optional description of what work is being done")

        @field_validator('target_path')
        @classmethod
        def validate_target_path(cls, v):
            if v and not TaskPath.validate_path(v):
                raise ValueError(f"Invalid task path format: {v}")
            return v

    class TimeSession(BaseModel):
        started_at: datetime = Field(description="When the session was started")
        ended_at: datetime = Field(description="When the session was ended")
        target_path: str = Field(description="The task path this session was targeting")
        duration: timedelta = Field(description="Duration of the session")
        description: Optional[str] = Field(default=None, description="Optional description of what work was done")
        session_type: SessionType = Field(default=SessionType.WORK, description="Type of session - work, break, or pause")

        @field_validator('target_path')
        @classmethod
        def validate_target_path(cls, v):
            if v and not TaskPath.validate_path(v):
                raise ValueError(f"Invalid task path format: {v}")
            return v

        @model_validator(mode='after')
        def validate_dates(self):
            if self.ended_at < self.started_at:
                raise ValueError("ended_at must be after started_at")
            return self

ProjectTimeTracker.model_rebuild()
