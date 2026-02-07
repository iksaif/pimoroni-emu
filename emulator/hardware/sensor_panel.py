"""Sensor control panel for the emulator UI.

Provides in-window sliders to control mock sensor values.
The panel auto-discovers sensors and only shows when sensors are used.
"""

from typing import Dict, List, Optional, Tuple, Callable, Any
from emulator import get_state

try:
    import pygame
except ImportError:
    pygame = None


class Slider:
    """Horizontal slider widget for controlling numeric values."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        min_val: float,
        max_val: float,
        value: float,
        label: str,
        format_str: str = "{:.1f}",
        on_change: Optional[Callable[[float], None]] = None,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.min_val = min_val
        self.max_val = max_val
        self._value = value
        self.label = label
        self.format_str = format_str
        self.on_change = on_change
        self.dragging = False

        # Colors
        self.bg_color = (40, 40, 40)
        self.track_color = (80, 80, 80)
        self.thumb_color = (100, 150, 200)
        self.thumb_hover_color = (120, 170, 220)
        self.text_color = (200, 200, 200)
        self.label_color = (150, 150, 150)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float):
        self._value = max(self.min_val, min(self.max_val, v))
        if self.on_change:
            self.on_change(self._value)

    def _value_to_x(self, val: float) -> int:
        """Convert value to x position."""
        ratio = (val - self.min_val) / (self.max_val - self.min_val)
        return int(self.x + 5 + ratio * (self.width - 10))

    def _x_to_value(self, x: int) -> float:
        """Convert x position to value."""
        ratio = (x - self.x - 5) / (self.width - 10)
        ratio = max(0, min(1, ratio))
        return self.min_val + ratio * (self.max_val - self.min_val)

    def hit_test(self, x: int, y: int) -> bool:
        """Check if point is within slider bounds."""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def handle_mouse(self, x: int, y: int, pressed: bool) -> bool:
        """Handle mouse input. Returns True if event was consumed."""
        if pressed:
            if self.hit_test(x, y):
                self.dragging = True
                self.value = self._x_to_value(x)
                return True
        else:
            self.dragging = False

        if self.dragging:
            self.value = self._x_to_value(x)
            return True

        return False

    def render(self, surface):
        """Render slider to pygame surface."""
        if pygame is None:
            return

        # Background
        pygame.draw.rect(surface, self.bg_color, (self.x, self.y, self.width, self.height))

        # Track
        track_y = self.y + self.height - 8
        pygame.draw.rect(surface, self.track_color, (self.x + 5, track_y, self.width - 10, 4))

        # Thumb
        thumb_x = self._value_to_x(self._value)
        thumb_color = self.thumb_hover_color if self.dragging else self.thumb_color
        pygame.draw.circle(surface, thumb_color, (thumb_x, track_y + 2), 6)

        # Label and value text
        font = pygame.font.SysFont("monospace", 10)
        label_surf = font.render(self.label, True, self.label_color)
        value_str = self.format_str.format(self._value)
        value_surf = font.render(value_str, True, self.text_color)

        surface.blit(label_surf, (self.x + 5, self.y + 2))
        surface.blit(value_surf, (self.x + self.width - value_surf.get_width() - 5, self.y + 2))


class SensorControl:
    """Control group for a sensor with multiple sliders."""

    def __init__(self, name: str, state_key: str, sliders: List[Tuple[str, str, float, float, float, str]]):
        """Create sensor control group.

        Args:
            name: Display name for the sensor
            state_key: Key to look up sensor in emulator state
            sliders: List of (label, attr_name, min, max, default, format) tuples
        """
        self.name = name
        self.state_key = state_key
        self.slider_specs = sliders
        self.sliders: List[Slider] = []
        self.expanded = True

    def create_sliders(self, x: int, y: int, width: int) -> int:
        """Create sliders and return total height used."""
        self.sliders = []
        current_y = y

        for label, attr_name, min_val, max_val, default, fmt in self.slider_specs:
            slider = Slider(
                x=x,
                y=current_y,
                width=width,
                height=24,
                min_val=min_val,
                max_val=max_val,
                value=default,
                label=label,
                format_str=fmt,
                on_change=lambda v, attr=attr_name: self._update_sensor(attr, v),
            )
            self.sliders.append(slider)
            current_y += 26

        return current_y - y

    def _update_sensor(self, attr_name: str, value: float):
        """Update sensor mock with new value."""
        state = get_state()
        sensor = state.get(self.state_key)
        if not sensor:
            return

        # Special handling for LSM6DS3 which uses tuples
        if self.state_key == "lsm6ds3":
            if attr_name.startswith("accel_"):
                current = list(sensor._accel)
                idx = {"accel_x": 0, "accel_y": 1, "accel_z": 2}.get(attr_name, 0)
                current[idx] = value
                sensor._set_values(accel=current)
            elif attr_name.startswith("gyro_"):
                current = list(sensor._gyro)
                idx = {"gyro_x": 0, "gyro_y": 1, "gyro_z": 2}.get(attr_name, 0)
                current[idx] = value
                sensor._set_values(gyro=current)
            return

        # Standard handling for other sensors
        if hasattr(sensor, "_set_values"):
            kwargs = {attr_name: value}
            sensor._set_values(**kwargs)

    def is_active(self) -> bool:
        """Check if this sensor is registered in state."""
        return get_state().get(self.state_key) is not None

    def sync_values(self):
        """Sync slider values from sensor state."""
        state = get_state()
        sensor = state.get(self.state_key)
        if not sensor:
            return

        for slider, (_, attr_name, _, _, _, _) in zip(self.sliders, self.slider_specs):
            # Special handling for LSM6DS3 which uses tuples
            if self.state_key == "lsm6ds3":
                if attr_name.startswith("accel_"):
                    idx = {"accel_x": 0, "accel_y": 1, "accel_z": 2}.get(attr_name, 0)
                    slider._value = sensor._accel[idx]
                elif attr_name.startswith("gyro_"):
                    idx = {"gyro_x": 0, "gyro_y": 1, "gyro_z": 2}.get(attr_name, 0)
                    slider._value = sensor._gyro[idx]
                continue

            # BME280 uses different names for storage vs setter
            # setter: temp, pressure, humidity
            # storage: _temperature, _pressure, _humidity
            storage_map = {
                "temp": "_temperature",
            }
            private_attr = storage_map.get(attr_name, f"_{attr_name}")

            if hasattr(sensor, private_attr):
                slider._value = getattr(sensor, private_attr)


# Define sensor configurations
# Note: attr_name must match the parameter names in each mock's _set_values() method
SENSOR_CONFIGS = [
    SensorControl("Battery", "battery", [
        ("Volts", "voltage", 3.0, 4.2, 3.7, "{:.2f}V"),
        ("Chg", "charging", 0, 1, 0, "{:.0f}"),
    ]),
    SensorControl("BME280", "bme280", [
        ("Temp", "temp", -40, 85, 22.5, "{:.1f}C"),  # Uses 'temp' in _set_values
        ("Press", "pressure", 300, 1100, 1013.25, "{:.0f}"),
        ("Humid", "humidity", 0, 100, 45.0, "{:.0f}%"),
    ]),
    SensorControl("LTR559", "ltr559", [
        ("Lux", "lux", 0, 65535, 100.0, "{:.0f}"),
        ("Prox", "proximity", 0, 65535, 0, "{:.0f}"),
    ]),
    SensorControl("LSM6DS3", "lsm6ds3", [
        ("Acc X", "accel_x", -16, 16, 0.0, "{:.2f}g"),
        ("Acc Y", "accel_y", -16, 16, 0.0, "{:.2f}g"),
        ("Acc Z", "accel_z", -16, 16, 1.0, "{:.2f}g"),
    ]),
]


class SensorPanel:
    """Collapsible panel for controlling sensor values."""

    def __init__(self, x: int, y: int, width: int = 120):
        self.x = x
        self.y = y
        self.width = width
        self.collapsed = False
        self.active_controls: List[SensorControl] = []
        self._needs_layout = True

        # Dragging state
        self._dragging = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._drag_moved = False

        # Colors
        self.bg_color = (30, 30, 35)
        self.header_color = (50, 50, 55)
        self.border_color = (60, 60, 65)
        self.text_color = (180, 180, 180)
        self.title_color = (140, 180, 220)

    def update(self):
        """Check for newly registered sensors and update layout."""
        # Find active sensors
        new_active = [ctrl for ctrl in SENSOR_CONFIGS if ctrl.is_active()]

        if new_active != self.active_controls:
            self.active_controls = new_active
            self._needs_layout = True

        if self._needs_layout and self.active_controls:
            self._layout()
            self._needs_layout = False

        # Sync values from sensors
        for ctrl in self.active_controls:
            ctrl.sync_values()

    def _layout(self):
        """Layout sliders for active sensors."""
        current_y = self.y + 25  # After header

        for ctrl in self.active_controls:
            if self.collapsed:
                continue
            current_y += 18  # Sensor name
            height = ctrl.create_sliders(self.x + 5, current_y, self.width - 10)
            current_y += height + 5

    def get_height(self) -> int:
        """Get total panel height."""
        if not self.active_controls:
            return 0
        if self.collapsed:
            return 25

        height = 25  # Header
        for ctrl in self.active_controls:
            height += 18  # Sensor name
            height += len(ctrl.sliders) * 26 + 5
        return height

    def has_sensors(self) -> bool:
        """Check if any sensors are active."""
        return len(self.active_controls) > 0

    def handle_mouse(self, x: int, y: int, pressed: bool) -> bool:
        """Handle mouse input. Returns True if event was consumed."""
        if not self.active_controls:
            return False

        # Handle drag release
        if not pressed and self._dragging:
            self._dragging = False
            if not self._drag_moved:
                # Click without moving = toggle collapse
                self.collapsed = not self.collapsed
                self._needs_layout = True
            return True

        # Handle active drag
        if self._dragging:
            dx = x - self._drag_offset_x - self.x
            dy = y - self._drag_offset_y - self.y
            if abs(dx) > 3 or abs(dy) > 3:
                self._drag_moved = True
            if self._drag_moved:
                self.x = x - self._drag_offset_x
                self.y = y - self._drag_offset_y
                self._needs_layout = True
            return True

        # Check header click - start potential drag
        if pressed and self.x <= x <= self.x + self.width and self.y <= y <= self.y + 20:
            self._dragging = True
            self._drag_moved = False
            self._drag_offset_x = x - self.x
            self._drag_offset_y = y - self.y
            return True

        if self.collapsed:
            return False

        # Check sliders
        for ctrl in self.active_controls:
            for slider in ctrl.sliders:
                if slider.handle_mouse(x, y, pressed):
                    return True

        return False

    def render(self, surface):
        """Render panel to pygame surface."""
        if pygame is None or not self.active_controls:
            return

        height = self.get_height()

        # Background
        pygame.draw.rect(surface, self.bg_color, (self.x, self.y, self.width, height))
        pygame.draw.rect(surface, self.border_color, (self.x, self.y, self.width, height), 1)

        # Header
        header_color = (60, 60, 65) if self._dragging else self.header_color
        pygame.draw.rect(surface, header_color, (self.x, self.y, self.width, 20))
        font = pygame.font.SysFont("monospace", 11)
        arrow = ">" if self.collapsed else "v"
        title = font.render(f"{arrow} Sensors", True, self.title_color)
        surface.blit(title, (self.x + 5, self.y + 3))

        # Drag handle dots (right side of header)
        grip_x = self.x + self.width - 14
        grip_color = (90, 90, 95)
        for row in range(3):
            for col in range(2):
                pygame.draw.rect(surface, grip_color,
                                 (grip_x + col * 4, self.y + 5 + row * 4, 2, 2))

        if self.collapsed:
            return

        # Render each sensor control
        current_y = self.y + 25
        name_font = pygame.font.SysFont("monospace", 10)

        for ctrl in self.active_controls:
            # Sensor name
            name_surf = name_font.render(ctrl.name, True, self.text_color)
            surface.blit(name_surf, (self.x + 5, current_y))
            current_y += 18

            # Sliders
            for slider in ctrl.sliders:
                slider.render(surface)
            current_y += len(ctrl.sliders) * 26 + 5
