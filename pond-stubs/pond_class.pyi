from .count_min_sketch import CountMinSketch as CountMinSketch
from .pooled_object import PooledObject as PooledObject
from .pooled_object_factory import PooledObjectFactory as PooledObjectFactory
from asyncio import AbstractEventLoop
from typing import Optional

class Pond:
    counter: CountMinSketch
    def __init__(self, borrowed_timeout: int = ..., time_between_eviction_runs: int = ..., eviction_weight: float = ..., thread_daemon: bool = ..., loop: AbstractEventLoop = ...) -> None: ...
    def register(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> None: ...
    def borrow(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> PooledObject: ...
    def recycle(self, pooled_object: PooledObject, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> None: ...
    def clear(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> None: ...
    def size(self) -> int: ...
    def count_total_objects(self) -> int: ...
    def pooled_object_size(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> int: ...
    def is_full(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> bool: ...
    def is_empty(self, factory: Optional[PooledObjectFactory] = ..., name: Optional[str] = ...) -> bool: ...
    def stop(self) -> None: ...
