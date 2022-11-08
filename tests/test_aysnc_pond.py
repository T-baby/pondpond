import asyncio
import time
from distutils.log import debug

import pytest

from pond import Pond, PooledObject, PooledObjectFactory


class Dog:
    name: str
    validate_result: bool = True


class PooledDogFactory(PooledObjectFactory):
    def creatInstantce(self) -> PooledObject:
        dog = Dog()
        dog.name = "puppy"
        return PooledObject(dog)

    def destroy(self, pooled_object: PooledObject) -> None:
        del pooled_object

    def reset(self, pooled_object: PooledObject) -> PooledObject:
        pooled_object.keeped_object.name = "puppy"
        return pooled_object

    def validate(self, pooled_object: PooledObject) -> bool:
        return pooled_object.keeped_object.validate_result


pooled_maxsize = 10
pond = Pond(
    borrowed_timeout=2,
    time_between_eviction_runs=-1,
    thread_daemon=True,
    eviction_weight=0.8,
)
factory = PooledDogFactory(pooled_maxsize=10, least_one=False)


@pytest.mark.run(order=1)
async def test_async_borrow_and_recycle() -> None:
    await pond.async_register(factory)
    pooled_object: PooledObject = await pond.async_borrow(factory)
    dog: Dog = pooled_object.use()
    assert dog.name == "puppy"
    assert pond.pooled_object_size(factory) == pooled_maxsize - 1
    assert pooled_object.keeped_object is dog
    await pond.async_recycle(pooled_object, factory)
    assert pond.pooled_object_size(factory) == pooled_maxsize
