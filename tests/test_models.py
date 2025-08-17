"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime, timedelta
from src.prismtm.models import (
    TaskStatus, BugStatus, BugSeverity, TaskPath,
    TaskTree, ProjectBugList, GlobalBugList,
    ProjectTimeTracker, SessionType
)


class TestTaskPath:
    """Test TaskPath validation and parsing."""

    def test_valid_paths(self):
        """Test valid task paths."""
        # Full path
        path = TaskPath("pa/0.2.x/0.2.2/task 1")
        assert path.phase == "pa"
        assert path.milestone == "0.2.x"
        assert path.block == "0.2.2"
        assert path.task == "task 1"

        # Partial paths
        path = TaskPath("alpha/1.0.x")
        assert path.phase == "alpha"
        assert path.milestone == "1.0.x"
        assert path.block is None
        assert path.task is None

    def test_invalid_paths(self):
        """Test invalid task paths."""
        with pytest.raises(ValueError, match="Invalid task path format"):
            TaskPath("invalid//path")

        with pytest.raises(ValueError, match="Invalid task path format"):
            TaskPath("")

    def test_path_validation(self):
        """Test path validation methods."""
        assert TaskPath.validate_path("pa/0.2.x/0.2.2/task 1")
        assert TaskPath.validate_path("alpha/1.0.x")
        assert not TaskPath.validate_path("invalid//path")

        assert TaskPath.validate_version("1.0.0")
        assert TaskPath.validate_version("0.1.x")
        assert not TaskPath.validate_version("invalid")

    def test_path_string_conversion(self):
        """Test converting path back to string."""
        original = "pa/0.2.x/0.2.2/task 1"
        path = TaskPath(original)
        assert str(path) == original


class TestSubTask:
    """Test SubTask model."""

    def test_valid_subtask(self):
        """Test creating a valid subtask."""
        subtask = TaskTree.SubTask(
            name="Test subtask",
            reason="Testing subtask creation",
            status=TaskStatus.NOT_STARTED
        )
        assert subtask.name == "Test subtask"
        assert subtask.status == TaskStatus.NOT_STARTED
        assert subtask.started_at is None
        assert subtask.finished_at is None

    def test_time_validation(self):
        """Test time validation."""
        now = datetime.now()
        future = now + timedelta(hours=1)

        # Valid times
        subtask = TaskTree.SubTask(
            name="Test",
            reason="Test",
            started_at=now,
            finished_at=future
        )
        assert subtask.started_at == now
        assert subtask.finished_at == future

        # Invalid times (finish before start)
        with pytest.raises(ValueError, match="finished_at must be after started_at"):
            TaskTree.SubTask(
                name="Test",
                reason="Test",
                started_at=future,
                finished_at=now
            )


class TestTask:
    """Test Task model."""

    def test_valid_task(self):
        """Test creating a valid task."""
        task = TaskTree.Task(
            name="Test task",
            reason="A test task",
            status=TaskStatus.IN_PROGRESS
        )
        assert task.name == "Test task"
        assert task.status == TaskStatus.IN_PROGRESS
        assert len(task.subtasks) == 0

    def test_task_with_subtasks(self):
        """Test task with subtasks."""
        subtask1 = TaskTree.SubTask(name="Sub 1", reason="First subtask")
        subtask2 = TaskTree.SubTask(name="Sub 2", reason="Second subtask")

        task = TaskTree.Task(
            name="Parent task",
            reason="Task with subtasks",
            subtasks=[subtask1, subtask2]
        )

        assert len(task.subtasks) == 2
        assert task.subtasks[0].name == "Sub 1"
        assert task.subtasks[1].name == "Sub 2"


class TestBlock:
    """Test Block model."""

    def test_valid_block(self):
        """Test creating a valid block."""
        block = TaskTree.Block(
            version="0.1.1",
            reason="Test block for version 0.1.1"
        )
        assert block.version == "0.1.1"
        assert block.reason == "Test block for version 0.1.1"
        assert len(block.tasks) == 0

    def test_version_validation(self):
        """Test version format validation."""
        # Valid versions
        TaskTree.Block(version="1.0.0", reason="Test")
        TaskTree.Block(version="0.1.1", reason="Test")

        # Invalid versions
        with pytest.raises(ValueError, match="Invalid version format"):
            TaskTree.Block(version="invalid", reason="Test")


class TestMilestone:
    """Test Milestone model."""

    def test_valid_milestone(self):
        """Test creating a valid milestone."""
        milestone = TaskTree.Milestone(
            versions="0.1.x",
            reason="Test milestone for 0.1.x versions"
        )
        assert milestone.versions == "0.1.x"
        assert milestone.reason == "Test milestone for 0.1.x versions"
        assert len(milestone.blocks) == 0

    def test_version_validation(self):
        """Test version format validation."""
        # Valid versions
        TaskTree.Milestone(versions="1.0.x", reason="Test")
        TaskTree.Milestone(versions="0.1.*", reason="Test")

        # Invalid versions
        with pytest.raises(ValueError, match="Invalid version format"):
            TaskTree.Milestone(versions="invalid", reason="Test")


class TestPhase:
    """Test Phase model."""

    def test_valid_phase(self):
        """Test creating a valid phase."""
        phase = TaskTree.Phase(
            name="pre-alpha",
            version_match="0.*.*"
        )
        assert phase.name == "pre-alpha"
        assert phase.version_match == "0.*.*"
        assert len(phase.milestones) == 0


class TestTaskTree:
    """Test TaskTree model."""

    def test_minimal_task_tree(self):
        """Test creating a minimal task tree."""
        tree = TaskTree(
            current_task_path="",
            nav_path="",
            phases=[]
        )
        assert tree.current_task_path == ""
        assert tree.nav_path == ""
        assert len(tree.phases) == 0

    def test_path_validation(self):
        """Test path validation in TaskTree."""
        # Valid paths
        TaskTree(
            current_task_path="pa/0.1.x/0.1.1/task1",
            nav_path="pa/0.1.x",
            phases=[]
        )

        # Invalid paths
        with pytest.raises(ValueError, match="Invalid task path format"):
            TaskTree(
                current_task_path="invalid//path",
                nav_path="",
                phases=[]
            )

    def test_find_by_path(self):
        """Test finding elements by path."""
        phase = TaskTree.Phase(name="pa", version_match="0.*.*")
        milestone = TaskTree.Milestone(versions="0.1.x", reason="Test milestone")
        block = TaskTree.Block(version="0.1.1", reason="Test block")
        task = TaskTree.Task(name="task1", reason="Test task")

        block.tasks.append(task)
        milestone.blocks.append(block)
        phase.milestones.append(milestone)

        tree = TaskTree(
            current_task_path="",
            nav_path="",
            phases=[phase]
        )

        # Test finding phase
        found_phase = tree.find_by_path("pa")
        assert found_phase == phase

        # Test finding milestone
        found_milestone = tree.find_by_path("pa/0.1.x")
        assert found_milestone == milestone

        # Test finding block
        found_block = tree.find_by_path("pa/0.1.x/0.1.1")
        assert found_block == block

        # Test finding task
        found_task = tree.find_by_path("pa/0.1.x/0.1.1/task1")
        assert found_task == task


class TestProjectBugList:
    """Test ProjectBugList model."""

    def test_valid_bug_list(self):
        """Test creating a valid project bug list."""
        bug_list = ProjectBugList()
        assert len(bug_list.tags) == 0
        assert len(bug_list.bugs) == 0

    def test_bug_creation(self):
        """Test creating bugs."""
        bug = ProjectBugList.Bug(
            id="BUG-001",
            title="Test bug",
            version="1.0.0",
            description="A test bug",
            status=BugStatus.OPEN,
            priority="high",
            opened_at=datetime.now()
        )
        assert bug.id == "BUG-001"
        assert bug.title == "Test bug"
        assert bug.status == BugStatus.OPEN


class TestGlobalBugList:
    """Test GlobalBugList model."""

    def test_valid_global_bug_list(self):
        """Test creating a valid global bug list."""
        bug_list = GlobalBugList()
        assert len(bug_list.tags) == 0
        assert len(bug_list.bugs) == 0

    def test_global_bug_creation(self):
        """Test creating global bugs."""
        bug = GlobalBugList.Bug(
            id="GLOBAL-001",
            project="test-project",
            title="Global test bug",
            version="1.0.0",
            description="A global test bug",
            status=BugStatus.OPEN,
            priority="medium",
            opened_at=datetime.now()
        )
        assert bug.id == "GLOBAL-001"
        assert bug.project == "test-project"
        assert bug.title == "Global test bug"
        assert bug.status == BugStatus.OPEN


class TestProjectTimeTracker:
    """Test ProjectTimeTracker model."""

    def test_empty_time_tracker(self):
        """Test creating an empty time tracker."""
        tracker = ProjectTimeTracker()
        assert tracker.current_session is None
        assert len(tracker.sessions) == 0

    def test_start_session(self):
        """Test starting a time tracking session."""
        tracker = ProjectTimeTracker()
        session = tracker.start_session("pa/0.1.x/0.1.1/task1", "Working on feature")

        assert tracker.current_session is not None
        assert tracker.current_session.target_path == "pa/0.1.x/0.1.1/task1"
        assert tracker.current_session.description == "Working on feature"
        assert isinstance(tracker.current_session.started_at, datetime)

    def test_start_session_when_active(self):
        """Test starting a session when one is already active."""
        tracker = ProjectTimeTracker()
        tracker.start_session("pa/0.1.x/0.1.1/task1")

        with pytest.raises(ValueError, match="A session is already active"):
            tracker.start_session("pa/0.1.x/0.1.1/task2")

    def test_stop_session(self):
        """Test stopping a time tracking session."""
        tracker = ProjectTimeTracker()
        tracker.start_session("pa/0.1.x/0.1.1/task1", "Working on feature")

        # Wait a tiny bit to ensure duration > 0
        import time
        time.sleep(0.01)

        completed_session = tracker.stop_session("Completed feature work")

        assert tracker.current_session is None
        assert len(tracker.sessions) == 1
        assert completed_session.target_path == "pa/0.1.x/0.1.1/task1"
        assert completed_session.description == "Completed feature work"
        assert completed_session.session_type == SessionType.WORK
        assert completed_session.duration > timedelta(0)

    def test_stop_session_when_none_active(self):
        """Test stopping a session when none is active."""
        tracker = ProjectTimeTracker()

        with pytest.raises(ValueError, match="No active session to stop"):
            tracker.stop_session()

    def test_get_total_time_for_path(self):
        """Test calculating total time for a specific path."""
        tracker = ProjectTimeTracker()

        # Add some completed sessions
        now = datetime.now()
        session1 = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=now + timedelta(hours=1),
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(hours=1),
            session_type=SessionType.WORK
        )
        session2 = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=now + timedelta(minutes=30),
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(minutes=30),
            session_type=SessionType.WORK
        )
        # Break session should not be counted
        session3 = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=now + timedelta(minutes=15),
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(minutes=15),
            session_type=SessionType.BREAK
        )

        tracker.sessions = [session1, session2, session3]

        total_time = tracker.get_total_time_for_path("pa/0.1.x/0.1.1/task1")
        assert total_time == timedelta(hours=1, minutes=30)

        # Different path should return zero
        other_total = tracker.get_total_time_for_path("pa/0.1.x/0.1.1/task2")
        assert other_total == timedelta(0)


class TestActiveTimeSession:
    """Test ActiveTimeSession model."""

    def test_valid_active_session(self):
        """Test creating a valid active session."""
        now = datetime.now()
        session = ProjectTimeTracker.ActiveTimeSession(
            started_at=now,
            target_path="pa/0.1.x/0.1.1/task1",
            description="Working on feature"
        )

        assert session.started_at == now
        assert session.target_path == "pa/0.1.x/0.1.1/task1"
        assert session.description == "Working on feature"

    def test_invalid_target_path(self):
        """Test validation of target path."""
        with pytest.raises(ValueError, match="Invalid task path format"):
            ProjectTimeTracker.ActiveTimeSession(
                started_at=datetime.now(),
                target_path="invalid//path"
            )


class TestTimeSession:
    """Test TimeSession model."""

    def test_valid_time_session(self):
        """Test creating a valid time session."""
        now = datetime.now()
        later = now + timedelta(hours=1)
        duration = timedelta(hours=1)

        session = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=later,
            target_path="pa/0.1.x/0.1.1/task1",
            duration=duration,
            description="Completed feature work",
            session_type=SessionType.WORK
        )

        assert session.started_at == now
        assert session.ended_at == later
        assert session.target_path == "pa/0.1.x/0.1.1/task1"
        assert session.duration == duration
        assert session.description == "Completed feature work"
        assert session.session_type == SessionType.WORK

    def test_invalid_time_order(self):
        """Test validation of time order."""
        now = datetime.now()
        earlier = now - timedelta(hours=1)

        with pytest.raises(ValueError, match="ended_at must be after started_at"):
            ProjectTimeTracker.TimeSession(
                started_at=now,
                ended_at=earlier,
                target_path="pa/0.1.x/0.1.1/task1",
                duration=timedelta(hours=1)
            )

    def test_invalid_target_path(self):
        """Test validation of target path."""
        now = datetime.now()
        later = now + timedelta(hours=1)

        with pytest.raises(ValueError, match="Invalid task path format"):
            ProjectTimeTracker.TimeSession(
                started_at=now,
                ended_at=later,
                target_path="invalid//path",
                duration=timedelta(hours=1)
            )

    def test_different_session_types(self):
        """Test different session types."""
        now = datetime.now()
        later = now + timedelta(minutes=30)

        # Work session
        work_session = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=later,
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(minutes=30),
            session_type=SessionType.WORK
        )
        assert work_session.session_type == SessionType.WORK

        # Break session
        break_session = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=later,
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(minutes=30),
            session_type=SessionType.BREAK
        )
        assert break_session.session_type == SessionType.BREAK

        # Pause session
        pause_session = ProjectTimeTracker.TimeSession(
            started_at=now,
            ended_at=later,
            target_path="pa/0.1.x/0.1.1/task1",
            duration=timedelta(minutes=30),
            session_type=SessionType.PAUSE
        )
        assert pause_session.session_type == SessionType.PAUSE
