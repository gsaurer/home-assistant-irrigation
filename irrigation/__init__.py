import asyncio
import logging
import voluptuous as vol

from homeassistant.core import callback
from datetime import (datetime, timedelta)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.util.dt as dt_util
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_ICON,
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP,
    SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON, STATE_OFF, MATCH_ALL)
from homeassistant.helpers.event import async_track_state_change


# Shortcut for the logger
_LOGGER = logging.getLogger(__name__)

DOMAIN = 'irrigation'
ENTITY_ID_FORMAT = DOMAIN + '.{}'
ZONE_DOMAIN = 'irrigation_zone'
ZONE_ENTITY_ID_FORMAT = ZONE_DOMAIN + '.{}'

PLATFORM_PROGRAM = 'program'
PLATFORM_ZONE = 'zone'
PLATFORMS = [PLATFORM_PROGRAM, PLATFORM_ZONE]

ATTR_IRRIG_ID = 'name'
ATTR_NAME = 'name'
ATTR_SWITCH = 'switch_entity'
ATTR_TEMPLATE = 'template'
ATTR_DURATION = 'duration'
ATTR_DURATION_REMAINING = 'duration_remaining'
ATTR_ZONES = 'zones'
ATTR_ZONE = 'zone'
ATTR_ENABLED = 'enabled'

ATTR_ICON = 'icon'
ATTR_ICON_OFF = 'icon_off'

ATTR_PROGRAMS = 'programs'
CONST_ENTITY = 'entity_id'
CONST_SWITCH = 'switch'
CONST_DATE_TIME_FORMAT = '%Y-%m-%d %H:%M'

DFLT_ICON_WATER = 'mdi:water'
DFLT_ICON_WATER_OFF = 'mdi:water-off'
DFLT_ICON_PROGRAM = 'mdi:fountain'
DFLT_ICON_PROGRAM_OFF = 'mdi:timer-off'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
            vol.Required(ATTR_ZONES): [{
                vol.Required(ATTR_IRRIG_ID): cv.string,
                vol.Optional(ATTR_DURATION): vol.Range(min=1, max=60),
                vol.Optional(ATTR_TEMPLATE): cv.template,
                vol.Required(ATTR_SWITCH): cv.entity_domain('switch'),
                vol.Optional(ATTR_ICON, default=DFLT_ICON_WATER): cv.icon,
                vol.Optional(ATTR_ICON_OFF, default=DFLT_ICON_WATER_OFF): cv.icon,
            }],
            vol.Required(ATTR_PROGRAMS): [{
                vol.Required(ATTR_IRRIG_ID): cv.string,
                vol.Required(ATTR_TEMPLATE): cv.template,
                vol.Optional(ATTR_ICON, default=DFLT_ICON_PROGRAM): cv.icon,
                vol.Optional(ATTR_ICON_OFF, default=DFLT_ICON_PROGRAM_OFF): cv.icon,
                vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
                vol.Required(ATTR_ZONES): [{
                    vol.Required(ATTR_ZONE): cv.entity_domain('irrigation_zone'),
                    vol.Required(ATTR_DURATION): vol.Range(min=1, max=60),
                }],
            }],
        }),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):

    @asyncio.coroutine
    def async_run_program_service(call):
        _LOGGER.info('async_run_program_service')
        entity_id = call.data.get(CONST_ENTITY)

        """ stop any running zones  before starting a new program"""
        hass.services.async_call(DOMAIN,
                                 'stop_programs',
                                 {})

        DATA = {}
        entity = component.get_entity(entity_id)
        if entity:
            target_irrigation = [entity]
            tasks = [irrigation.async_run_program(DATA)
                     for irrigation in target_irrigation]
            if tasks:
                yield from asyncio.wait(tasks, loop=hass.loop)
        else:
            _LOGGER.error('irrigation program not found: %s', entity_id)
    """ END async_run_program_service """

    @asyncio.coroutine
    def async_stop_program_service(call):
        _LOGGER.info('async_stop_program_service')
        entity_id = call.data.get(CONST_ENTITY)
        entity = component.get_entity(entity_id)
        if entity:
            target_irrigation = [entity]
            tasks = [irrigation.async_stop_program()
                     for irrigation in target_irrigation]
            if tasks:
                yield from asyncio.wait(tasks, loop=hass.loop)
        else:
            _LOGGER.error('irrigation program not found: %s',
                          entity_id)
    """ END async_stop_program_service """

    @asyncio.coroutine
    def async_run_zone_service(call):
        _LOGGER.info('async_run_zone_service')
        entity_id = call.data.get(CONST_ENTITY)
        duration = call.data.get(ATTR_DURATION, 0)

        DATA = {ATTR_DURATION: duration}
        entity = component.get_entity(entity_id)
        if entity:
            target_irrigation = [entity]
            tasks = [irrigation_zone.async_run_zone(DATA)
                     for irrigation_zone in target_irrigation]
            if tasks:
                yield from asyncio.wait(tasks, loop=hass.loop)
        else:
            _LOGGER.error('irrigation_zone not found: %s', entity_id)
    """ END async_run_zone_service """

    @asyncio.coroutine
    def async_stop_zone_service(call):
        _LOGGER.info('async_stop_zone_service')
        entity_id = call.data.get(CONST_ENTITY)
        entity = component.get_entity(entity_id)
        if entity:
            target_irrigation = [entity]
            tasks = [irrigation_zone.async_stop_zone()
                     for irrigation_zone in target_irrigation]
            if tasks:
                yield from asyncio.wait(tasks, loop=hass.loop)
        else:
            _LOGGER.error('irrigation_zone not found: %s',
                          entity_id)
    """ END async_stop_zone_service """

    @asyncio.coroutine
    def async_stop_programs_service(call):
        _LOGGER.info('async_stop_programs_service')
        for program in conf.get(ATTR_PROGRAMS):
            irrigation_id = cv.slugify(program.get(ATTR_IRRIG_ID))
            entity_id = ENTITY_ID_FORMAT.format(irrigation_id)
            entity = component.get_entity(entity_id)
            if entity:
                target_irrigation = [entity]
                tasks = [irrigation.async_stop_program()
                        for irrigation in target_irrigation]
                if tasks:
                    yield from asyncio.wait(tasks, loop=hass.loop)
            else:
                _LOGGER.error('irrigation program not found: %s',
                            entity_id)

        for zone in conf.get(ATTR_ZONES):
            irrigation_id = cv.slugify(zone.get(ATTR_IRRIG_ID))
            entity_id = ZONE_ENTITY_ID_FORMAT.format(irrigation_id)
            entity = component.get_entity(entity_id)
            if entity:
                target_irrigation = [entity]
                tasks = [irrigation_zone.async_stop_zone()
                        for irrigation_zone in target_irrigation]
                if tasks:
                    yield from asyncio.wait(tasks, loop=hass.loop)
            else:
                _LOGGER.error('irrigation_zone not found: %s',
                            entity_id)
    """ END async_stop_programs_service """

    @asyncio.coroutine
    def async_stop_switches(call):
        _LOGGER.info('async_stop_switches')
        for zone in conf.get(ATTR_ZONES):
            irrigation_id = cv.slugify(zone.get(ATTR_IRRIG_ID))
            entity_id = ZONE_ENTITY_ID_FORMAT.format(irrigation_id)
            entity = component.get_entity(entity_id)
            if entity:
                target_irrigation = [entity]
                tasks = [irrigation_zone.async_stop_switch()
                         for irrigation_zone in target_irrigation]
                if tasks:
                    yield from asyncio.wait(tasks, loop=hass.loop)
            else:
                _LOGGER.error('irrigation_zone not found: %s', entity_id)
    """ END async_stop_switches """

    """ create the entities and time tracking on setup of the component """
    conf = config[DOMAIN]
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    """ parse progams """
    programentities = []
    for program in conf.get(ATTR_PROGRAMS):
        irrigation_id = cv.slugify(program.get(ATTR_IRRIG_ID))
        template = program.get(ATTR_TEMPLATE)
        if template is not None:
            template.hass = hass
            p_entity = ENTITY_ID_FORMAT.format(irrigation_id)
            programentities.append(Irrigation(p_entity,
                                              program,
                                              component))
            _LOGGER.info('Irrigation %s added', irrigation_id)
            if(not program.get(ATTR_ENABLED)):
                _LOGGER.warn('Irrigation %s disabled', irrigation_id)
    await component.async_add_entities(programentities)

    """ parse zones """
    zoneentities = []
    for zone in conf.get(ATTR_ZONES):
        irrigation_id = cv.slugify(zone.get(ATTR_IRRIG_ID))
        p_entity = ZONE_ENTITY_ID_FORMAT.format(irrigation_id)
        zoneentities.append(IrrigationZone(p_entity,
                                           zone))
        _LOGGER.info('Zone %s added', p_entity)
    await component.async_add_entities(zoneentities)

    """ define services """
    hass.services.async_register(DOMAIN,
                                 'run_program',
                                 async_run_program_service)
    hass.services.async_register(DOMAIN,
                                 'stop_program',
                                 async_stop_program_service)
    hass.services.async_register(DOMAIN,
                                 'run_zone',
                                 async_run_zone_service)
    hass.services.async_register(DOMAIN,
                                 'stop_zone',
                                 async_stop_zone_service)
    hass.services.async_register(DOMAIN,
                                 'stop_programs',
                                 async_stop_programs_service)

    return True


class Irrigation(RestoreEntity):
    """Representation of an Irrigation program."""

    def __init__(self, irrigation_id, attributes, component):
        """Initialize a Irrigation program."""
        self.entity_id = irrigation_id
        self._attributes = attributes
        self._component = component
        self._name = attributes.get(ATTR_NAME)
        self._zones = attributes.get(ATTR_ZONES)
        self._icon_on = attributes.get(ATTR_ICON,
                                       DFLT_ICON_PROGRAM)
        self._icon_off = attributes.get(ATTR_ICON_OFF,
                                        DFLT_ICON_PROGRAM_OFF)
        self._stop = False
        """ default to today for new programs """
        self._last_run = dt_util.as_local(
            dt_util.now()).strftime(CONST_DATE_TIME_FORMAT)
        self._template = attributes.get(ATTR_TEMPLATE)
        self._enabled = attributes.get(ATTR_ENABLED)
        self._running = False
        self._running_zone = None
        self._state_attributes = {}

    async def async_added_to_hass(self):

        """ Run when entity about to be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        if state:
            """ handle bad data or new entity"""
            try:
                if not cv.date(state.state):
                    self._last_run = dt_util.as_local(
                        date.fromtimestamp(0)).strftime(CONST_DATE_TIME_FORMAT)
                else:
                    self._last_run = state.state
             except:
                self._last_run = dt_util.as_local(
                    date.fromtimestamp(0)).strftime(CONST_DATE_TIME_FORMAT)

        self.async_schedule_update_ha_state(True)

        """Register callbacks. From Template same model as template sensor"""
        @callback
        def template_sensor_state_listener(entity, old_state, new_state):
            """Handle device state changes."""
            self.async_schedule_update_ha_state(True)

        @callback
        def template_sensor_startup(event):
            """Update template on startup."""
            if self._entities != MATCH_ALL:
                # Track state change only for valid templates
                async_track_state_change(
                    self.hass, self._entities, template_sensor_state_listener)

            self.async_schedule_update_ha_state(True)

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, template_sensor_startup)

    @property
    def should_poll(self):
        """If entity should be polled."""
        return True

    @property
    def name(self):
        """Return the name of the variable."""
        if not self._enabled:
            x = '{}, disabled'.format(
                self._name)
        elif self._running:
            x = '{}, running {}.'.format(
                self._name, self._running_zone)
        else:
            x = '{}, last ran {}'.format(
                self._name, self._last_run)
        return x

    def is_on(self):
        """If the switch is currently on or off."""
        return self._running

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self._running:
            return self._icon_on
        else:
            return self._icon_off

    @property
    def state(self):
        """Return the state of the component."""
        if self._running:
            return STATE_ON
        else:
            return STATE_OFF

    @property
    def state_attributes(self):
        """Return the state attributes.
        Implemented by component base class.
        """
        return self._state_attributes

    @asyncio.coroutine
    async def async_update(self):
        _LOGGER.info('async_update - %s', self.entity_id)

        """ assess the template """
        if self._template is not None:
            self._template.hass = self.hass
            try:
                trigger_run = self._template.async_render()
                if self._enabled == True and trigger_run == 'True' and self._running == False:
                    """ if evaluates to true start service """
                    DATA = {CONST_ENTITY: self.entity_id}
                    await self.hass.services.async_call(DOMAIN,
                                                        'run_program',
                                                        DATA)
            except:
                _LOGGER.error('Program template %s, invalid: %s',
                              self._name,
                              self._template)
                return

    @asyncio.coroutine
    async def async_stop_program(self):
        _LOGGER.warn('async_stop_program - %s', self.entity_id)
        self._stop = True
        self.async_schedule_update_ha_state()

    @asyncio.coroutine
    async def async_run_program(self, DATA):
        _LOGGER.warn('async_run_program - %s', self.entity_id)
        self._stop = False

        """ don't assess the template - was done before """

        if self._enabled == True and self._running == False:
            _LOGGER.warn('Starting Program %s', self._name)
            self._running = True
            self._last_run = dt_util.as_local(
                dt_util.now()).strftime(CONST_DATE_TIME_FORMAT)
            self._stop = False

            """ Iterate through all the defined zones """
            for zone in self._zones:
                if not self._stop:
                    zone_id = zone.get(ATTR_ZONE)
                    duration = int(zone.get(ATTR_DURATION, 0))

                    DATA = {CONST_ENTITY: zone_id,
                            ATTR_DURATION: duration}
                    await self.hass.services.async_call(DOMAIN,
                                                        'run_zone',
                                                        DATA)

                    zone = self._component.get_entity(zone_id)
                    self._running_zone = zone.name
                    self.async_schedule_update_ha_state(True)

                    """ wait for the state to take """
                    await asyncio.sleep(1)

                    """ monitor the zone state """
                    while zone.state != STATE_OFF:
                        await asyncio.sleep(1)
                        if self._stop == True:
                            await self.hass.services.async_call(DOMAIN,
                                                                'stop_zone',
                                                                DATA)
                            break
                    self._running_zone = None

        self._stop = True
        self._running = False
        self.async_schedule_update_ha_state(True)
        _LOGGER.warn('Finishing Program %s', self._name)


class IrrigationZone(Entity):
    """Representation of an Irrigation zone."""

    def __init__(self, irrigation_id, attributes):
        """Initialize a Irrigation program."""
        self.entity_id = irrigation_id
        self._name = attributes.get(ATTR_NAME)
        self._switch = attributes.get(ATTR_SWITCH)
        self._duration = int(attributes.get(ATTR_DURATION))
        self._state = STATE_OFF
        self._icon_on = attributes.get(ATTR_ICON,
                                       DFLT_ICON_WATER)
        self._icon_off = attributes.get(ATTR_ICON_OFF,
                                        DFLT_ICON_WATER_OFF)
        self._state = STATE_OFF
        self._stop = False
        self._template = attributes.get(ATTR_TEMPLATE)
        self._runtime_remaining = 0
        self._state_attributes = {
            ATTR_DURATION_REMAINING: self._runtime_remaining}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        """ house keeping to help ensure solenoids are in a safe state """
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, self.async_stop_switch())
        return True

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the variable."""
        if self._state == STATE_ON:
            x = '{} remaining {} (m).'.format(
                self._name, self._runtime_remaining
            )
        else:
            x = '{} def. duration {} (m).'.format(
                self._name, self._duration)
        return x

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self._state == STATE_ON:
            return self._icon_on
        else:
            return self._icon_off

    def is_on(self):
        """If the switch is currently on or off."""
        return self._state == STATE_ON

    @property
    def state(self):
        """Return the state of the component."""
        return self._state

    @property
    def state_attributes(self):
        """Return the state attributes.
        Implemented by component base class.
        """
        return self._state_attributes

    @asyncio.coroutine
    async def async_update(self):
        """Update the state from the template."""
        _LOGGER.info('async_update - %s', self.entity_id)

    @asyncio.coroutine
    async def async_stop_zone(self):
        _LOGGER.warn('async_stop_zone - %s', self.entity_id)
        self._stop = True
        DATA = {ATTR_ENTITY_ID: self._switch}
        await self.hass.services.async_call(CONST_SWITCH,
                                            SERVICE_TURN_OFF,
                                            DATA)
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

    @asyncio.coroutine
    async def async_stop_switch(self):
        _LOGGER.warn('async_stop_switch - %s', self._switch)
        DATA = {ATTR_ENTITY_ID: self._switch}
        await self.hass.services.async_call(CONST_SWITCH,
                                            SERVICE_TURN_OFF,
                                            DATA)
        self._state = STATE_OFF

    @asyncio.coroutine
    async def async_run_zone(self, DATA):
        _LOGGER.info('async_run_zone - %s', self._name)

        self._stop = False
        duration = int(DATA.get(ATTR_DURATION, self._duration))
        if duration == 0:
            duration = self._duration

        """ assess the template program internally triggered"""
        trigger_run = 'True'
        if self._template is not None:
            self._template.hass = self.hass
            try:
                trigger_run = self._template.async_render()
            except:
                _LOGGER.error('zone template %s, invalid: %s',
                              self._name,
                              self._template)
                return

        if trigger_run == 'True':

            """ run the watering cycle, water/wait/repeat """
            watering = duration * 60
            self._runtime_remaining = duration

            if self._stop == False:
                _LOGGER.warn('Starting Zone %s', self._name)
                self._state = STATE_ON
                self.async_schedule_update_ha_state(True)
                DATA = {ATTR_ENTITY_ID: self._switch}
                await self.hass.services.async_call(CONST_SWITCH,
                                                    SERVICE_TURN_ON,
                                                    DATA)

                for second in range(watering):
                    if second / 60 == 0:
                        self._runtime_remaining = self._runtime_remaining - 1
                        self.async_schedule_update_ha_state()
                    await asyncio.sleep(1)
                    if self._stop == True:
                        break

            await self.hass.services.async_call(CONST_SWITCH,
                                                SERVICE_TURN_OFF,
                                                DATA)

            self._runtime_remaining = 0
            self._state = STATE_OFF
            self.async_schedule_update_ha_state(True)
            _LOGGER.warn('Finishing Zone %s', self._name)
            return True
