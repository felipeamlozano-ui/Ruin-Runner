"""
Ruin Engine V3.0 — Asynchronous Threading & Background Worker Pool.
Dispatches heavy procedural computation, noise field generation, and radiance cache baking
off the main render thread to prevent frame drops.
"""

import queue
import threading
from typing import Callable, Any, Optional

class AsyncTask:
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.result: Any = None
        self.completed: bool = False
        self.error: Optional[Exception] = None

class ThreadWorkerPool:
    """
    Dedicated background worker thread pool for non-blocking procedural baking and cache calculations.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, num_workers: int = 2):
        if getattr(self, "_initialized", False):
            return
            
        self.task_queue: queue.Queue[AsyncTask] = queue.Queue()
        self.completed_tasks: dict[str, AsyncTask] = {}
        self.workers: list[threading.Thread] = []
        self.running: bool = True
        
        for i in range(num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"RuinWorker-{i}")
            t.start()
            self.workers.append(t)
            
        self._initialized = True

    def _worker_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                task.result = task.func(*task.args, **task.kwargs)
            except Exception as e:
                task.error = e
            finally:
                task.completed = True
                self.completed_tasks[task.task_id] = task
                self.task_queue.task_done()

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> AsyncTask:
        """Submits a workload to be executed in the background."""
        task = AsyncTask(task_id, func, args, kwargs)
        self.task_queue.put(task)
        return task

    def poll_result(self, task_id: str) -> Optional[Any]:
        """Polls for task completion without blocking."""
        if task_id in self.completed_tasks:
            task = self.completed_tasks.pop(task_id)
            if task.error:
                raise task.error
            return task.result
        return None

    def shutdown(self):
        self.running = False


WORKER_POOL = ThreadWorkerPool()
