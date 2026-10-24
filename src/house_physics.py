"""Deterministic illustrative 1s household model; uncalibrated synthetic data."""
from __future__ import annotations

RATINGS = {'fridge': 120., 'kettle': 1500., 'fan': 45., 'lights': 54.,
           'tv': 80., 'router': 10., 'aircon': 800., 'rice_cooker': 600., 'washer': 400.}


class HouseholdPhysics:
    def __init__(self) -> None:
        self.ambient_c = 30.
        self.fridge_c = 5.
        self.room_c = 30.
        self.water_c = 25.
        self.water_kg = 1.
        self.door_open = False
        self.compressor_on = True
        self.aircon_on = True
        self.kettle_stage = 'idle'
        self.rice_stage = 'idle'
        self.washer_stage = 'idle'
        self.requests = dict.fromkeys(RATINGS, False)
        self.rice_seconds = 0
        self.washer_seconds = 0
        self.energy = dict.fromkeys(RATINGS, 0.)

    def advance(self, modes: dict[str, str], elapsed: int) -> dict[str, float]:
        """Return powers held during this second and integrate end-of-second state."""
        seconds = (22800 + elapsed) % 86400
        hour = seconds / 3600
        scheduled = {
            'fridge': True, 'router': True,
            'kettle': 23400 <= seconds < 23700 or 72000 <= seconds < 72300,
            'fan': 11 <= hour < 14 or 18 <= hour < 23,
            'lights': 18 <= hour < 23, 'tv': 19 <= hour < 22,
            'aircon': 18 <= hour < 23,
            'rice_cooker': 6 <= hour < 7 or 17 <= hour < 18,
            'washer': 8 <= hour < 9,
        }
        requested = {k: scheduled[k] if mode == 'auto' else mode == 'on'
                     for k, mode in modes.items()}
        power = {k: RATINGS[k] if enabled else 0. for k, enabled in requested.items()}

        if self.fridge_c >= 5:
            self.compressor_on = True
        elif self.fridge_c <= 3:
            self.compressor_on = False
        cooling = requested['fridge'] and self.compressor_on
        power['fridge'] = (2. + 120. * cooling) if requested['fridge'] else 0.
        self.fridge_c += (2 * (self.ambient_c - self.fridge_c)
                          + 150 * self.door_open - 180 * cooling) / 20000

        if self.room_c >= 26:
            self.aircon_on = True
        elif self.room_c <= 25:
            self.aircon_on = False
        cooling = requested['aircon'] and self.aircon_on
        power['aircon'] = (30. + 800. * cooling) if requested['aircon'] else 0.
        self.room_c += (120 * (self.ambient_c - self.room_c)
                        + (30 if requested['aircon'] else 0) - 2400 * cooling) / 2e6

        if not requested['kettle']:
            self.kettle_stage = 'idle'
        elif not self.requests['kettle']:
            self.kettle_stage = 'heating' if self.water_c < 100 else 'boiled'
        power['kettle'] = 1500. if self.kettle_stage == 'heating' else 0.
        self.water_c += (power['kettle'] - 2 * (self.water_c - self.ambient_c)) / (4186 * self.water_kg)
        if self.water_c >= 100:
            self.water_c = 100.
            self.kettle_stage = 'boiled' if requested['kettle'] else 'idle'

        if not requested['rice_cooker']:
            self.rice_seconds = 0
            self.rice_stage = 'idle'
        else:
            self.rice_stage = 'cooking' if self.rice_seconds < 1200 else 'warm'
            self.rice_seconds += 1
        power['rice_cooker'] = {'idle': 0., 'cooking': 600., 'warm': 40.}[self.rice_stage]

        if not requested['washer']:
            self.washer_seconds = 0
            self.washer_stage = 'idle'
        else:
            t = self.washer_seconds
            self.washer_stage = 'wash' if t < 600 else 'rinse' if t < 900 else 'spin' if t < 1200 else 'done'
            self.washer_seconds += 1
        power['washer'] = {'idle': 0., 'wash': 400., 'rinse': 100., 'spin': 300., 'done': 0.}[self.washer_stage]
        self.requests = requested
        for name, value in power.items():
            self.energy[name] += value / 3.6e6
        return power

    def snapshot(self) -> dict[str, object]:
        return {'profile': 'thermal_synthetic', 'ambient_c': self.ambient_c,
                'fridge_c': self.fridge_c, 'room_c': self.room_c, 'water_c': self.water_c,
                'water_kg': self.water_kg, 'fridge_door_open': self.door_open,
                'stages': {'fridge': 'cooling' if self.requests['fridge'] and self.compressor_on else 'rest',
                           'aircon': 'cooling' if self.requests['aircon'] and self.aircon_on else 'rest',
                           'kettle': self.kettle_stage, 'rice_cooker': self.rice_stage,
                           'washer': self.washer_stage},
                'energy_kwh': dict(self.energy), 'total_kwh': sum(self.energy.values())}
