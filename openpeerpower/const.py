# coding: utf-8
"""Constants used by OPP components."""
MAJOR_VERSION = 0
MINOR_VERSION = 1
PATCH_VERSION = '0.dev0'
__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)
REQUIRED_PYTHON_VER = (3, 5, 3)

# Format for platforms
PLATFORM_FORMAT = '{}.{}'

# Can be used to specify a catch all when registering state or event listeners.
MATCH_ALL = '*'

# If no name is specified
DEVICE_DEFAULT_NAME = 'Unnamed Device'

# Sun events
SUN_EVENT_SUNSET = 'sunset'
SUN_EVENT_SUNRISE = 'sunrise'

# #### EVENTS ####
EVENT_OPENPEERPOWER_START = 'opp_start'
EVENT_OPENPEERPOWER_STOP = 'opp_stop'
EVENT_OPENPEERPOWER_CLOSE = 'opp_close'
EVENT_STATE_CHANGED = 'state_changed'
EVENT_TIME_CHANGED = 'time_changed'
EVENT_CALL_SERVICE = 'call_service'
EVENT_SERVICE_EXECUTED = 'service_executed'
EVENT_PLATFORM_DISCOVERED = 'platform_discovered'
EVENT_COMPONENT_LOADED = 'component_loaded'
EVENT_SERVICE_REGISTERED = 'service_registered'
EVENT_SERVICE_REMOVED = 'service_removed'
EVENT_LOGBOOK_ENTRY = 'logbook_entry'
EVENT_THEMES_UPDATED = 'themes_updated'
EVENT_TIMER_OUT_OF_SYNC = 'timer_out_of_sync'

# #### DEVICE CLASSES ####
DEVICE_CLASS_BATTERY = 'battery'
DEVICE_CLASS_HUMIDITY = 'humidity'
DEVICE_CLASS_ILLUMINANCE = 'illuminance'
DEVICE_CLASS_TEMPERATURE = 'temperature'
DEVICE_CLASS_PRESSURE = 'pressure'

# #### STATES ####
STATE_ON = 'on'
STATE_OFF = 'off'
STATE_HOME = 'home'
STATE_NOT_HOME = 'not_home'
STATE_UNKNOWN = 'unknown'
STATE_OPEN = 'open'
STATE_OPENING = 'opening'
STATE_CLOSED = 'closed'
STATE_CLOSING = 'closing'
STATE_PLAYING = 'playing'
STATE_PAUSED = 'paused'
STATE_IDLE = 'idle'
STATE_STANDBY = 'standby'
STATE_ALARM_DISARMED = 'disarmed'
STATE_ALARM_ARMED_HOME = 'armed_home'
STATE_ALARM_ARMED_AWAY = 'armed_away'
STATE_ALARM_ARMED_NIGHT = 'armed_night'
STATE_ALARM_ARMED_CUSTOM_BYPASS = 'armed_custom_bypass'
STATE_ALARM_PENDING = 'pending'
STATE_ALARM_ARMING = 'arming'
STATE_ALARM_DISARMING = 'disarming'
STATE_ALARM_TRIGGERED = 'triggered'
STATE_LOCKED = 'locked'
STATE_UNLOCKED = 'unlocked'
STATE_UNAVAILABLE = 'unavailable'
STATE_OK = 'ok'
STATE_PROBLEM = 'problem'

# #### STATE AND EVENT ATTRIBUTES ####
# Attribution
ATTR_ATTRIBUTION = 'attribution'

# Credentials
ATTR_CREDENTIALS = 'credentials'

# Contains time-related attributes
ATTR_NOW = 'now'
ATTR_DATE = 'date'
ATTR_TIME = 'time'
ATTR_SECONDS = 'seconds'

# Contains domain, service for a SERVICE_CALL event
ATTR_DOMAIN = 'domain'
ATTR_SERVICE = 'service'
ATTR_SERVICE_DATA = 'service_data'

# IDs
ATTR_ID = 'id'

# Name
ATTR_NAME = 'name'

# Data for a SERVICE_EXECUTED event
ATTR_SERVICE_CALL_ID = 'service_call_id'

# Contains one string or a list of strings, each being an entity id
ATTR_ENTITY_ID = 'entity_id'

# String with a friendly name for the entity
ATTR_FRIENDLY_NAME = 'friendly_name'

# A picture to represent entity
ATTR_ENTITY_PICTURE = 'entity_picture'

# Icon to use in the frontend
ATTR_ICON = 'icon'

# The unit of measurement if applicable
ATTR_UNIT_OF_MEASUREMENT = 'unit_of_measurement'

CONF_UNIT_SYSTEM_METRIC = 'metric'  # type: str
CONF_UNIT_SYSTEM_IMPERIAL = 'imperial'  # type: str

# Electrical attributes
ATTR_VOLTAGE = 'voltage'

# Contains the information that is discovered
ATTR_DISCOVERED = 'discovered'

# Location of the device/sensor
ATTR_LOCATION = 'location'

ATTR_BATTERY_CHARGING = 'battery_charging'
ATTR_BATTERY_LEVEL = 'battery_level'
ATTR_WAKEUP = 'wake_up_interval'

# For devices which support a code attribute
ATTR_CODE = 'code'
ATTR_CODE_FORMAT = 'code_format'

# For calling a device specific command
ATTR_COMMAND = 'command'

# For devices which support an armed state
ATTR_ARMED = 'device_armed'

# For devices which support a locked state
ATTR_LOCKED = 'locked'

# For sensors that support 'tripping', eg. motion and door sensors
ATTR_TRIPPED = 'device_tripped'

# For sensors that support 'tripping' this holds the most recent
# time the device was tripped
ATTR_LAST_TRIP_TIME = 'last_tripped_time'

# For all entity's, hidden status
ATTR_HIDDEN = 'hidden'

# Location of the entity
ATTR_LATITUDE = 'latitude'
ATTR_LONGITUDE = 'longitude'

# Accuracy of location in meters
ATTR_GPS_ACCURACY = 'gps_accuracy'

# If state is assumed
ATTR_ASSUMED_STATE = 'assumed_state'
ATTR_STATE = 'state'

ATTR_OPTION = 'option'

# Bitfield of supported component features for the entity
ATTR_SUPPORTED_FEATURES = 'supported_features'

# Class of device within its domain
ATTR_DEVICE_CLASS = 'device_class'

# Temperature attribute
ATTR_TEMPERATURE = 'temperature'

# #### UNITS OF MEASUREMENT ####
# Temperature units
TEMP_CELSIUS = '°C'
TEMP_FAHRENHEIT = '°F'

# Length units
LENGTH_CENTIMETERS = 'cm'  # type: str
LENGTH_METERS = 'm'  # type: str
LENGTH_KILOMETERS = 'km'  # type: str

LENGTH_INCHES = 'in'  # type: str
LENGTH_FEET = 'ft'  # type: str
LENGTH_YARD = 'yd'  # type: str
LENGTH_MILES = 'mi'  # type: str

# Volume units
VOLUME_LITRES = 'L'  # type: str
VOLUME_MILLILITRES = 'mL'  # type: str

VOLUME_GALLONS = 'gal'  # type: str
VOLUME_FLUID_OUNCE = 'fl. oz.'  # type: str

# Mass units
MASS_GRAMS = 'g'  # type: str
MASS_KILOGRAMS = 'kg'  # type: str

MASS_OUNCES = 'oz'  # type: str
MASS_POUNDS = 'lb'  # type: str

# UV Index units
UNIT_UV_INDEX = 'UV index'  # type: str

# #### SERVICES ####
SERVICE_OPENPEERPOWER_STOP = 'stop'
SERVICE_OPENPEERPOWER_RESTART = 'restart'

SERVICE_TURN_ON = 'turn_on'
SERVICE_TURN_OFF = 'turn_off'
SERVICE_TOGGLE = 'toggle'
SERVICE_RELOAD = 'reload'

SERVICE_VOLUME_UP = 'volume_up'
SERVICE_VOLUME_DOWN = 'volume_down'
SERVICE_VOLUME_MUTE = 'volume_mute'
SERVICE_VOLUME_SET = 'volume_set'
SERVICE_MEDIA_PLAY_PAUSE = 'media_play_pause'
SERVICE_MEDIA_PLAY = 'media_play'
SERVICE_MEDIA_PAUSE = 'media_pause'
SERVICE_MEDIA_STOP = 'media_stop'
SERVICE_MEDIA_NEXT_TRACK = 'media_next_track'
SERVICE_MEDIA_PREVIOUS_TRACK = 'media_previous_track'
SERVICE_MEDIA_SEEK = 'media_seek'
SERVICE_SHUFFLE_SET = 'shuffle_set'

SERVICE_ALARM_DISARM = 'alarm_disarm'
SERVICE_ALARM_ARM_HOME = 'alarm_arm_home'
SERVICE_ALARM_ARM_AWAY = 'alarm_arm_away'
SERVICE_ALARM_ARM_NIGHT = 'alarm_arm_night'
SERVICE_ALARM_ARM_CUSTOM_BYPASS = 'alarm_arm_custom_bypass'
SERVICE_ALARM_TRIGGER = 'alarm_trigger'


SERVICE_LOCK = 'lock'
SERVICE_UNLOCK = 'unlock'

SERVICE_OPEN = 'open'
SERVICE_CLOSE = 'close'

SERVICE_CLOSE_COVER = 'close_cover'
SERVICE_CLOSE_COVER_TILT = 'close_cover_tilt'
SERVICE_OPEN_COVER = 'open_cover'
SERVICE_OPEN_COVER_TILT = 'open_cover_tilt'
SERVICE_SET_COVER_POSITION = 'set_cover_position'
SERVICE_SET_COVER_TILT_POSITION = 'set_cover_tilt_position'
SERVICE_STOP_COVER = 'stop_cover'
SERVICE_STOP_COVER_TILT = 'stop_cover_tilt'

SERVICE_SELECT_OPTION = 'select_option'

# The exit code to send to request a restart
RESTART_EXIT_CODE = 100

UNIT_NOT_RECOGNIZED_TEMPLATE = '{} is not a recognized {} unit.'  # type: str

LENGTH = 'length'  # type: str
MASS = 'mass'  # type: str
VOLUME = 'volume'  # type: str
TEMPERATURE = 'temperature'  # type: str
SPEED_MS = 'speed_ms'  # type: str
ILLUMINANCE = 'illuminance'  # type: str

WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# The degree of precision for platforms
PRECISION_WHOLE = 1
PRECISION_HALVES = 0.5
PRECISION_TENTHS = 0.1
