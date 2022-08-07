from distutils.log import debug
import time
import pytest
from pond import Pond, PooledObjectFactory, PooledObject


class Dog:
    name: str
    validate_result: bool = True


class PooledDogFactory(PooledObjectFactory):
    def creatInstantce(self) -> PooledObject:
        dog = Dog()
        dog.name = "puppy"
        return PooledObject(dog)

    def destroy(self, pooled_object: PooledObject):
        del pooled_object

    def reset(self, pooled_object: PooledObject) -> PooledObject:
        pooled_object.keeped_object.name = "puppy"
        return pooled_object

    def validate(self, pooled_object: PooledObject) -> bool:
        return pooled_object.keeped_object.validate_result


pooled_maxsize = 10
pond = Pond(borrowed_timeout=2,
            time_between_eviction_runs=-1, thread_daemon=True, eviction_weight=0.8)
factory = PooledDogFactory(pooled_maxsize=10, least_one=False)


@pytest.mark.run(order=1)
def test_register():
    assert(factory.pooled_maxsize == pooled_maxsize)
    pond.register(factory)


@pytest.mark.run(order=1)
def test_register_by_name():
    pond.register(factory, name="PuppyFactory")
    assert(pond.size() == 2)


@pytest.mark.run(order=2)
def test_pooled_object_size():
    assert(pond.pooled_object_size(factory) == pooled_maxsize)


@pytest.mark.run(order=2)
def test_pooled_is_full():
    assert(pond.is_full(factory))


@pytest.mark.run(order=2)
def test_pooled_is_empty():
    assert(pond.is_empty(factory) == False)


@pytest.mark.run(order=2)
def test_counter():
    pond.recycle(pond.borrow(factory), factory)
    assert(pond.counter[factory.factory_name()] == 1)
    pond.recycle(pond.borrow(factory), factory)
    assert(pond.counter[factory.factory_name()] == 2)


@pytest.mark.run(order=2)
def test_count_total_objects():
    assert(pond.count_total_objects() == 20)


@pytest.mark.run(order=2)
def test_count_total_objects():
    assert(pond.count_total_objects() == 20)


@pytest.mark.run(order=3)
def test_borrow_and_recycle():
    pooled_object: PooledObject = pond.borrow(factory)
    dog: Dog = pooled_object.use()
    assert(dog.name == "puppy")
    assert(pond.pooled_object_size(factory) == pooled_maxsize - 1)
    assert(pooled_object.keeped_object is dog)
    pond.recycle(pooled_object, factory)
    assert(pond.pooled_object_size(factory) == pooled_maxsize)


@pytest.mark.run(order=3)
def test_validate():
    pond.register(factory, name="test_validate")
    pond.clear(name="test_validate")
    dog = Dog()
    dog.validate_result = False
    pooled_object: PooledObject = PooledObject(dog)
    pond.recycle(pooled_object, name="test_validate")
    assert(pond.pooled_object_size(name="test_validate") == 1)
    pooled_object = pond.borrow(name="test_validate")
    assert(pooled_object.keeped_object.validate_result)


@pytest.mark.run(order=3)
def test_borrow_and_recycle_by_name():
    pooled_object: PooledObject = pond.borrow(name="PuppyFactory")
    dog: Dog = pooled_object.use()
    assert(dog.name == "puppy")
    assert(pond.pooled_object_size(
        name="PuppyFactory") == pooled_maxsize - 1)
    assert(pooled_object.keeped_object is dog)
    pond.recycle(pooled_object, name="PuppyFactory")
    assert(pond.pooled_object_size(name="PuppyFactory") == pooled_maxsize)


@pytest.mark.run(order=3)
def test_recycle_and_reset():
    pooled_object: PooledObject = pond.borrow(factory)
    dog: Dog = pooled_object.use()
    assert(dog.name == "puppy")
    dog.name = "dinosaurs"
    pond.recycle(pooled_object, factory)
    pooled_object: PooledObject = pond.borrow(factory)
    dog: Dog = pooled_object.use()
    assert(dog.name == "puppy")
    pond.recycle(pooled_object, factory)


@pytest.mark.run(order=3)
def test_borrowed_timeout():
    pooled_object: PooledObject = pond.borrow(factory)
    dog: Dog = pooled_object.use()
    assert(dog.name == "puppy")
    assert(pond.pooled_object_size(factory) == pooled_maxsize - 1)
    time.sleep(2)
    pond.recycle(pooled_object, factory)
    assert(pond.pooled_object_size(factory) == pooled_maxsize - 1)


@pytest.mark.run(order=3)
def test_borrow_when_queue_empty():
    for i in range(pooled_maxsize):
        pond.borrow(factory)
    assert(pond.pooled_object_size(factory) == 0)
    pooled_object = pond.borrow(factory)
    assert(pooled_object)
    pond.recycle(pooled_object, factory)
    assert(pond.pooled_object_size(factory) > 0)


@pytest.mark.run(order=4)
@pytest.mark.asyncio
async def test_eviction():
    pond._Pond__time_between_eviction_runs = 1
    await pond._Pond__eviction(debug=True)


@pytest.mark.run(order=998)
def test_clear():
    assert(pond.pooled_object_size(factory) > 0)
    pond.clear(factory)
    assert(pond.pooled_object_size(factory) == 0)


@pytest.mark.run(order=999)
def test_stop():
    pond.stop()
