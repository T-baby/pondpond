import abc
from .pooled_object import PooledObject as PooledObject
from _typeshed import Incomplete

class PooledObjectFactory(metaclass=abc.ABCMeta):
    pooled_maxsize: Incomplete
    least_one: Incomplete
    def __init__(self, pooled_maxsize: int = ..., least_one: bool = ...) -> None: ...
    @abc.abstractmethod
    def creatInstantce(self) -> PooledObject: ...
    @abc.abstractmethod
    def destroy(self, pooled_object: PooledObject) -> None: ...
    @abc.abstractmethod
    def reset(self, pooled_object: PooledObject) -> PooledObject: ...
    @abc.abstractmethod
    def validate(self, pooled_object: PooledObject) -> bool: ...
    def factory_name(self) -> str: ...
