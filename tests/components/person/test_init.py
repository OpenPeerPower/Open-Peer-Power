"""The tests for the person component."""
import logging

from asynctest import patch
import pytest

from openpeerpower.components import person
from openpeerpower.components.device_tracker import (
    ATTR_SOURCE_TYPE,
    SOURCE_TYPE_GPS,
    SOURCE_TYPE_ROUTER,
)
from openpeerpower.components.person import ATTR_SOURCE, ATTR_USER_ID, DOMAIN
from openpeerpower.const import (
    ATTR_GPS_ACCURACY,
    ATTR_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    EVENT_OPENPEERPOWER_START,
    SERVICE_RELOAD,
    STATE_UNKNOWN,
)
from openpeerpower.core import Context, CoreState, State
from openpeerpower.helpers import collection, entity_registry
from openpeerpower.setup import async_setup_component

from tests.common import assert_setup_component, mock_component, mock_restore_cache

DEVICE_TRACKER = "device_tracker.test_tracker"
DEVICE_TRACKER_2 = "device_tracker.test_tracker_2"


@pytest.fixture
def storage_collection(opp):
    """Return an empty storage collection."""
    id_manager = collection.IDManager()
    return person.PersonStorageCollection(
        person.PersonStore(opp, person.STORAGE_VERSION, person.STORAGE_KEY),
        logging.getLogger(f"{person.__name__}.storage_collection"),
        id_manager,
        collection.YamlCollection(
            logging.getLogger(f"{person.__name__}.yaml_collection"), id_manager
        ),
    )


@pytest.fixture
def storage_setup(opp, opp_storage, opp_admin_user):
    """Storage setup."""
    opp_storage[DOMAIN] = {
        "key": DOMAIN,
        "version": 1,
        "data": {
            "persons": [
                {
                    "id": "1234",
                    "name": "tracked person",
                    "user_id": opp_admin_user.id,
                    "device_trackers": [DEVICE_TRACKER],
                }
            ]
        },
    }
    assert opp.loop.run_until_complete(async_setup_component(opp, DOMAIN, {}))


async def test_minimal_setup(opp):
    """Test minimal config with only name."""
    config = {DOMAIN: {"id": "1234", "name": "test person"}}
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.test_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) is None


async def test_setup_no_id(opp):
    """Test config with no id."""
    config = {DOMAIN: {"name": "test user"}}
    assert not await async_setup_component(opp, DOMAIN, config)


async def test_setup_no_name(opp):
    """Test config with no name."""
    config = {DOMAIN: {"id": "1234"}}
    assert not await async_setup_component(opp, DOMAIN, config)


async def test_setup_user_id(opp, opp_admin_user):
    """Test config with user id."""
    user_id = opp_admin_user.id
    config = {DOMAIN: {"id": "1234", "name": "test person", "user_id": user_id}}
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.test_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id


async def test_valid_invalid_user_ids(opp, opp_admin_user):
    """Test a person with valid user id and a person with invalid user id ."""
    user_id = opp_admin_user.id
    config = {
        DOMAIN: [
            {"id": "1234", "name": "test valid user", "user_id": user_id},
            {"id": "5678", "name": "test bad user", "user_id": "bad_user_id"},
        ]
    }
    with assert_setup_component(2):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.test_valid_user")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id
    state = opp.states.get("person.test_bad_user")
    assert state is None


async def test_setup_tracker(opp, opp_admin_user):
    """Test set up person with one device tracker."""
    opp.state = CoreState.not_running
    user_id = opp_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": DEVICE_TRACKER,
        }
    }
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id

    opp.states.async_set(DEVICE_TRACKER, "home")
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id

    opp.states.async_set(
        DEVICE_TRACKER,
        "not_home",
        {ATTR_LATITUDE: 10.123456, ATTR_LONGITUDE: 11.123456, ATTR_GPS_ACCURACY: 10},
    )
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "not_home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 10.123456
    assert state.attributes.get(ATTR_LONGITUDE) == 11.123456
    assert state.attributes.get(ATTR_GPS_ACCURACY) == 10
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id


async def test_setup_two_trackers(opp, opp_admin_user):
    """Test set up person with two device trackers."""
    opp.state = CoreState.not_running
    user_id = opp_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": [DEVICE_TRACKER, DEVICE_TRACKER_2],
        }
    }
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    await opp.async_block_till_done()
    opp.states.async_set(DEVICE_TRACKER, "home", {ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER})
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_GPS_ACCURACY) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id

    opp.states.async_set(
        DEVICE_TRACKER_2,
        "not_home",
        {
            ATTR_LATITUDE: 12.123456,
            ATTR_LONGITUDE: 13.123456,
            ATTR_GPS_ACCURACY: 12,
            ATTR_SOURCE_TYPE: SOURCE_TYPE_GPS,
        },
    )
    await opp.async_block_till_done()
    opp.states.async_set(
        DEVICE_TRACKER, "not_home", {ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER}
    )
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "not_home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 12.123456
    assert state.attributes.get(ATTR_LONGITUDE) == 13.123456
    assert state.attributes.get(ATTR_GPS_ACCURACY) == 12
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER_2
    assert state.attributes.get(ATTR_USER_ID) == user_id

    opp.states.async_set(DEVICE_TRACKER_2, "zone1", {ATTR_SOURCE_TYPE: SOURCE_TYPE_GPS})
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "zone1"
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER_2

    opp.states.async_set(DEVICE_TRACKER, "home", {ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER})
    await opp.async_block_till_done()
    opp.states.async_set(DEVICE_TRACKER_2, "zone2", {ATTR_SOURCE_TYPE: SOURCE_TYPE_GPS})
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER


async def test_ignore_unavailable_states(opp, opp_admin_user):
    """Test set up person with two device trackers, one unavailable."""
    opp.state = CoreState.not_running
    user_id = opp_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": [DEVICE_TRACKER, DEVICE_TRACKER_2],
        }
    }
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    await opp.async_block_till_done()
    opp.states.async_set(DEVICE_TRACKER, "home")
    await opp.async_block_till_done()
    opp.states.async_set(DEVICE_TRACKER, "unavailable")
    await opp.async_block_till_done()

    # Unknown, as only 1 device tracker has a state, but we ignore that one
    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    opp.states.async_set(DEVICE_TRACKER_2, "not_home")
    await opp.async_block_till_done()

    # Take state of tracker 2
    state = opp.states.get("person.tracked_person")
    assert state.state == "not_home"

    # state 1 is newer but ignored, keep tracker 2 state
    opp.states.async_set(DEVICE_TRACKER, "unknown")
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "not_home"


async def test_restore_home_state(opp, opp_admin_user):
    """Test that the state is restored for a person on startup."""
    user_id = opp_admin_user.id
    attrs = {
        ATTR_ID: "1234",
        ATTR_LATITUDE: 10.12346,
        ATTR_LONGITUDE: 11.12346,
        ATTR_SOURCE: DEVICE_TRACKER,
        ATTR_USER_ID: user_id,
    }
    state = State("person.tracked_person", "home", attrs)
    mock_restore_cache(opp, (state,))
    opp.state = CoreState.not_running
    mock_component(opp, "recorder")
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": DEVICE_TRACKER,
        }
    }
    with assert_setup_component(1):
        assert await async_setup_component(opp, DOMAIN, config)

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 10.12346
    assert state.attributes.get(ATTR_LONGITUDE) == 11.12346
    # When restoring state the entity_id of the person will be used as source.
    assert state.attributes.get(ATTR_SOURCE) == "person.tracked_person"
    assert state.attributes.get(ATTR_USER_ID) == user_id


async def test_duplicate_ids(opp, opp_admin_user):
    """Test we don't allow duplicate IDs."""
    config = {
        DOMAIN: [
            {"id": "1234", "name": "test user 1"},
            {"id": "1234", "name": "test user 2"},
        ]
    }
    with assert_setup_component(2):
        assert await async_setup_component(opp, DOMAIN, config)

    assert len(opp.states.async_entity_ids("person")) == 1
    assert opp.states.get("person.test_user_1") is not None
    assert opp.states.get("person.test_user_2") is None


async def test_create_person_during_run(opp):
    """Test that person is updated if created while opp is running."""
    config = {DOMAIN: {}}
    with assert_setup_component(0):
        assert await async_setup_component(opp, DOMAIN, config)
    opp.states.async_set(DEVICE_TRACKER, "home")
    await opp.async_block_till_done()

    await opp.components.person.async_create_person(
        "tracked person", device_trackers=[DEVICE_TRACKER]
    )
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"


async def test_load_person_storage(opp, opp_admin_user, storage_setup):
    """Test set up person from storage."""
    state = opp.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == opp_admin_user.id

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    await opp.async_block_till_done()
    opp.states.async_set(DEVICE_TRACKER, "home")
    await opp.async_block_till_done()

    state = opp.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == opp_admin_user.id


async def test_load_person_storage_two_nonlinked(opp, opp_storage):
    """Test loading two users with both not having a user linked."""
    opp_storage[DOMAIN] = {
        "key": DOMAIN,
        "version": 1,
        "data": {
            "persons": [
                {
                    "id": "1234",
                    "name": "tracked person 1",
                    "user_id": None,
                    "device_trackers": [],
                },
                {
                    "id": "5678",
                    "name": "tracked person 2",
                    "user_id": None,
                    "device_trackers": [],
                },
            ]
        },
    }
    await async_setup_component(opp, DOMAIN, {})

    assert len(opp.states.async_entity_ids("person")) == 2
    assert opp.states.get("person.tracked_person_1") is not None
    assert opp.states.get("person.tracked_person_2") is not None


async def test_ws_list(opp, opp_ws_client, storage_setup):
    """Test listing via WS."""
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)

    resp = await client.send_json({"id": 6, "type": "person/list"})
    resp = await client.receive_json()
    assert resp["success"]
    assert resp["result"]["storage"] == manager.async_items()
    assert len(resp["result"]["storage"]) == 1
    assert len(resp["result"]["config"]) == 0


async def test_ws_create(opp, opp_ws_client, storage_setup, opp_read_only_user):
    """Test creating via WS."""
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/create",
            "name": "Hello",
            "device_trackers": [DEVICE_TRACKER],
            "user_id": opp_read_only_user.id,
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 2

    assert resp["success"]
    assert resp["result"] == persons[1]


async def test_ws_create_requires_admin(
    opp, opp_ws_client, storage_setup, opp_admin_user, opp_read_only_user
):
    """Test creating via WS requires admin."""
    opp_admin_user.groups = []
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/create",
            "name": "Hello",
            "device_trackers": [DEVICE_TRACKER],
            "user_id": opp_read_only_user.id,
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 1

    assert not resp["success"]


async def test_ws_update(opp, opp_ws_client, storage_setup):
    """Test updating via WS."""
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)
    persons = manager.async_items()

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/update",
            "person_id": persons[0]["id"],
            "user_id": persons[0]["user_id"],
        }
    )
    resp = await client.receive_json()

    assert resp["success"]

    resp = await client.send_json(
        {
            "id": 7,
            "type": "person/update",
            "person_id": persons[0]["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 1

    assert resp["success"]
    assert resp["result"] == persons[0]
    assert persons[0]["name"] == "Updated Name"
    assert persons[0]["name"] == "Updated Name"
    assert persons[0]["device_trackers"] == [DEVICE_TRACKER_2]
    assert persons[0]["user_id"] is None

    state = opp.states.get("person.tracked_person")
    assert state.name == "Updated Name"


async def test_ws_update_require_admin(
    opp, opp_ws_client, storage_setup, opp_admin_user
):
    """Test updating via WS requires admin."""
    opp_admin_user.groups = []
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)
    original = dict(manager.async_items()[0])

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/update",
            "person_id": original["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]

    not_updated = dict(manager.async_items()[0])
    assert original == not_updated


async def test_ws_delete(opp, opp_ws_client, storage_setup):
    """Test deleting via WS."""
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)
    persons = manager.async_items()

    resp = await client.send_json(
        {"id": 6, "type": "person/delete", "person_id": persons[0]["id"]}
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 0

    assert resp["success"]
    assert len(opp.states.async_entity_ids("person")) == 0
    ent_reg = await opp.helpers.entity_registry.async_get_registry()
    assert not ent_reg.async_is_registered("person.tracked_person")


async def test_ws_delete_require_admin(
    opp, opp_ws_client, storage_setup, opp_admin_user
):
    """Test deleting via WS requires admin."""
    opp_admin_user.groups = []
    manager = opp.data[DOMAIN][1]

    client = await opp_ws_client(opp)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/delete",
            "person_id": manager.async_items()[0]["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]

    persons = manager.async_items()
    assert len(persons) == 1


async def test_create_invalid_user_id(opp, storage_collection):
    """Test we do not allow invalid user ID during creation."""
    with pytest.raises(ValueError):
        await storage_collection.async_create_item(
            {"name": "Hello", "user_id": "non-existing"}
        )


async def test_create_duplicate_user_id(opp, opp_admin_user, storage_collection):
    """Test we do not allow duplicate user ID during creation."""
    await storage_collection.async_create_item(
        {"name": "Hello", "user_id": opp_admin_user.id}
    )

    with pytest.raises(ValueError):
        await storage_collection.async_create_item(
            {"name": "Hello", "user_id": opp_admin_user.id}
        )


async def test_update_double_user_id(opp, opp_admin_user, storage_collection):
    """Test we do not allow double user ID during update."""
    await storage_collection.async_create_item(
        {"name": "Hello", "user_id": opp_admin_user.id}
    )
    person = await storage_collection.async_create_item({"name": "Hello"})

    with pytest.raises(ValueError):
        await storage_collection.async_update_item(
            person["id"], {"user_id": opp_admin_user.id}
        )


async def test_update_invalid_user_id(opp, storage_collection):
    """Test updating to invalid user ID."""
    person = await storage_collection.async_create_item({"name": "Hello"})

    with pytest.raises(ValueError):
        await storage_collection.async_update_item(
            person["id"], {"user_id": "non-existing"}
        )


async def test_update_person_when_user_removed(opp, storage_setup, opp_read_only_user):
    """Update person when user is removed."""
    storage_collection = opp.data[DOMAIN][1]

    person = await storage_collection.async_create_item(
        {"name": "Hello", "user_id": opp_read_only_user.id}
    )

    await opp.auth.async_remove_user(opp_read_only_user)
    await opp.async_block_till_done()

    assert storage_collection.data[person["id"]]["user_id"] is None


async def test_removing_device_tracker(opp, storage_setup):
    """Test we automatically remove removed device trackers."""
    storage_collection = opp.data[DOMAIN][1]
    reg = await entity_registry.async_get_registry(opp)
    entry = reg.async_get_or_create(
        "device_tracker", "mobile_app", "bla", suggested_object_id="pixel"
    )

    person = await storage_collection.async_create_item(
        {"name": "Hello", "device_trackers": [entry.entity_id]}
    )

    reg.async_remove(entry.entity_id)
    await opp.async_block_till_done()

    assert storage_collection.data[person["id"]]["device_trackers"] == []


async def test_add_user_device_tracker(opp, storage_setup, opp_read_only_user):
    """Test adding a device tracker to a person tied to a user."""
    storage_collection = opp.data[DOMAIN][1]
    pers = await storage_collection.async_create_item(
        {
            "name": "Hello",
            "user_id": opp_read_only_user.id,
            "device_trackers": ["device_tracker.on_create"],
        }
    )

    await person.async_add_user_device_tracker(
        opp, opp_read_only_user.id, "device_tracker.added"
    )

    assert storage_collection.data[pers["id"]]["device_trackers"] == [
        "device_tracker.on_create",
        "device_tracker.added",
    ]


async def test_reload(opp, opp_admin_user):
    """Test reloading the YAML config."""
    assert await async_setup_component(
        opp,
        DOMAIN,
        {
            DOMAIN: [
                {"name": "Person 1", "id": "id-1"},
                {"name": "Person 2", "id": "id-2"},
            ]
        },
    )

    assert len(opp.states.async_entity_ids()) == 2

    state_1 = opp.states.get("person.person_1")
    state_2 = opp.states.get("person.person_2")
    state_3 = opp.states.get("person.person_3")

    assert state_1 is not None
    assert state_1.name == "Person 1"
    assert state_2 is not None
    assert state_2.name == "Person 2"
    assert state_3 is None

    with patch(
        "openpeerpower.config.load_yaml_config_file",
        autospec=True,
        return_value={
            DOMAIN: [
                {"name": "Person 1-updated", "id": "id-1"},
                {"name": "Person 3", "id": "id-3"},
            ]
        },
    ):
        await opp.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            blocking=True,
            context=Context(user_id=opp_admin_user.id),
        )
        await opp.async_block_till_done()

    assert len(opp.states.async_entity_ids()) == 2

    state_1 = opp.states.get("person.person_1")
    state_2 = opp.states.get("person.person_2")
    state_3 = opp.states.get("person.person_3")

    assert state_1 is not None
    assert state_1.name == "Person 1-updated"
    assert state_2 is None
    assert state_3 is not None
    assert state_3.name == "Person 3"


async def test_person_storage_fixing_device_trackers(storage_collection):
    """Test None device trackers become lists."""
    with patch.object(
        storage_collection.store,
        "async_load",
        return_value={"items": [{"id": "bla", "name": "bla", "device_trackers": None}]},
    ):
        await storage_collection.async_load()

    assert storage_collection.data["bla"]["device_trackers"] == []
