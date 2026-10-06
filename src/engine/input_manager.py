"""
Ruin Runner — Multi-Player Input Architecture & Device Abstraction.
Supports simultaneous 2-Player Local Co-op on:
- Same keyboard without key ghosting / conflict (WASD vs Numpad/Arrows)
- Keyboard P1 + Gamepad P2
- Gamepad P1 + Keyboard P2
- Gamepad P1 + Gamepad P2
Full action abstraction: InputAction, PlayerInput, and InputManager.
"""

import pygame
from typing import Dict, Set, List, Optional, Union
from config.controls import (
    InputAction,
    P1_DEFAULT_KEYBOARD,
    P2_DEFAULT_KEYBOARD,
    DEFAULT_GAMEPAD
)

class PlayerInput:
    """Input controller for a single player instance (P1 or P2)."""
    def __init__(
        self,
        player_index: int,
        key_bindings: Dict[str, List[int]],
        pad_bindings: Dict[str, int],
        device_type: str = "auto"
    ):
        self.player_index = player_index
        self.device_type = device_type # "keyboard", "gamepad", "auto"
        self.key_bindings = {k: list(v) for k, v in key_bindings.items()}
        self.pad_bindings = dict(pad_bindings)
        
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.keys_pressed: Set[int] = set()
        self.keys_just_pressed: Set[int] = set()
        self.keys_just_released: Set[int] = set()
        
        self.pad_buttons_pressed: Set[int] = set()
        self.pad_buttons_just_pressed: Set[int] = set()
        self.pad_buttons_just_released: Set[int] = set()

    def set_joystick(self, joystick: Optional[pygame.joystick.Joystick]):
        self.joystick = joystick

    def clear(self):
        self.keys_pressed.clear()
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()
        self.pad_buttons_pressed.clear()
        self.pad_buttons_just_pressed.clear()
        self.pad_buttons_just_released.clear()

    def update_frame(self):
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()
        self.pad_buttons_just_pressed.clear()
        self.pad_buttons_just_released.clear()

    def process_key_down(self, key: int):
        self.keys_pressed.add(key)
        self.keys_just_pressed.add(key)

    def process_key_up(self, key: int):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
        self.keys_just_released.add(key)

    def process_joy_button_down(self, joy_id: int, button: int):
        if self.joystick and self.joystick.get_instance_id() == joy_id:
            self.pad_buttons_pressed.add(button)
            self.pad_buttons_just_pressed.add(button)

    def process_joy_button_up(self, joy_id: int, button: int):
        if self.joystick and self.joystick.get_instance_id() == joy_id:
            if button in self.pad_buttons_pressed:
                self.pad_buttons_pressed.remove(button)
            self.pad_buttons_just_released.add(button)

    def _normalize_action(self, action: Union[str, InputAction]) -> str:
        if isinstance(action, InputAction):
            return action.value
        act = action.upper()
        if act == "MAGIC":
            return "SKILL"
        return act

    def is_action_pressed(self, action: Union[str, InputAction]) -> bool:
        act_name = self._normalize_action(action)
        
        # Check Keyboard
        if self.device_type in ("keyboard", "auto"):
            keys = pygame.key.get_pressed()
            if act_name in self.key_bindings:
                for k in self.key_bindings[act_name]:
                    if k < len(keys) and keys[k]:
                        return True
                    if k in self.keys_pressed:
                        return True

        # Check Gamepad
        if self.joystick and self.device_type in ("gamepad", "auto"):
            if act_name in self.pad_bindings:
                btn = self.pad_bindings[act_name]
                if btn in self.pad_buttons_pressed:
                    return True
                try:
                    if self.joystick.get_button(btn):
                        return True
                except Exception:
                    pass

        return False

    def is_action_just_pressed(self, action: Union[str, InputAction]) -> bool:
        act_name = self._normalize_action(action)
        
        if self.device_type in ("keyboard", "auto"):
            if act_name in self.key_bindings:
                for k in self.key_bindings[act_name]:
                    if k in self.keys_just_pressed:
                        return True

        if self.joystick and self.device_type in ("gamepad", "auto"):
            if act_name in self.pad_bindings:
                btn = self.pad_bindings[act_name]
                if btn in self.pad_buttons_just_pressed:
                    return True

        return False

    def is_action_just_released(self, action: Union[str, InputAction]) -> bool:
        act_name = self._normalize_action(action)
        
        if self.device_type in ("keyboard", "auto"):
            if act_name in self.key_bindings:
                for k in self.key_bindings[act_name]:
                    if k in self.keys_just_released:
                        return True

        if self.joystick and self.device_type in ("gamepad", "auto"):
            if act_name in self.pad_bindings:
                btn = self.pad_bindings[act_name]
                if btn in self.pad_buttons_just_released:
                    return True

        return False

    def get_axis(self) -> pygame.math.Vector2:
        axis = pygame.math.Vector2(0, 0)
        
        if self.is_action_pressed("LEFT"): axis.x -= 1
        if self.is_action_pressed("RIGHT"): axis.x += 1
        if self.is_action_pressed("UP"): axis.y -= 1
        if self.is_action_pressed("DOWN"): axis.y += 1
        
        # Override / augment with gamepad analog stick or D-pad
        if self.joystick and self.device_type in ("gamepad", "auto"):
            try:
                # Analog stick axes (Axis 0 = X, Axis 1 = Y)
                ax = self.joystick.get_axis(0)
                ay = self.joystick.get_axis(1)
                deadzone = 0.25
                if abs(ax) > deadzone:
                    axis.x = 1.0 if ax > 0 else -1.0
                if abs(ay) > deadzone:
                    axis.y = 1.0 if ay > 0 else -1.0
                    
                # D-pad hat
                hat = self.joystick.get_hat(0)
                if hat != (0, 0):
                    axis.x = float(hat[0])
                    axis.y = -float(hat[1])
            except Exception:
                pass
                
        return axis


class InputManager:
    """Global Input orchestrator for Single Player and Local Co-op."""
    def __init__(self):
        self.p1 = PlayerInput(0, P1_DEFAULT_KEYBOARD, DEFAULT_GAMEPAD, device_type="auto")
        self.p2 = PlayerInput(1, P2_DEFAULT_KEYBOARD, DEFAULT_GAMEPAD, device_type="auto")
        self.joysticks: List[pygame.joystick.Joystick] = []

    def init(self):
        """Discovers and initializes all connected gamepads."""
        pygame.joystick.init()
        self.joysticks.clear()
        count = pygame.joystick.get_count()
        for i in range(count):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.joysticks.append(joy)
            except Exception as e:
                print(f"Notice: Joystick {i} init: {e}")
                
        # Assign joysticks automatically
        if len(self.joysticks) >= 1:
            self.p1.set_joystick(self.joysticks[0])
        if len(self.joysticks) >= 2:
            self.p2.set_joystick(self.joysticks[1])

    def get_player(self, player_index: int = 0) -> PlayerInput:
        return self.p1 if player_index == 0 else self.p2

    def clear(self):
        self.p1.clear()
        self.p2.clear()

    def update(self):
        self.p1.update_frame()
        self.p2.update_frame()

    def process_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            self.p1.process_key_down(event.key)
            self.p2.process_key_down(event.key)
        elif event.type == pygame.KEYUP:
            self.p1.process_key_up(event.key)
            self.p2.process_key_up(event.key)
        elif event.type == pygame.JOYBUTTONDOWN:
            self.p1.process_joy_button_down(event.instance_id, event.button)
            self.p2.process_joy_button_down(event.instance_id, event.button)
        elif event.type == pygame.JOYBUTTONUP:
            self.p1.process_joy_button_up(event.instance_id, event.button)
            self.p2.process_joy_button_up(event.instance_id, event.button)
        elif event.type == pygame.JOYDEVICEADDED or event.type == pygame.JOYDEVICEREMOVED:
            self.init()

    # Legacy singleton methods forwarding to Player 1
    def is_action_pressed(self, action: Union[str, InputAction]) -> bool:
        return self.p1.is_action_pressed(action)

    def is_action_just_pressed(self, action: Union[str, InputAction]) -> bool:
        return self.p1.is_action_just_pressed(action)

    def is_action_just_released(self, action: Union[str, InputAction]) -> bool:
        return self.p1.is_action_just_released(action)

    def get_axis(self) -> pygame.math.Vector2:
        return self.p1.get_axis()

    def reset_defaults(self, player_index: int = 0):
        if player_index == 0:
            self.p1.key_bindings = {k: list(v) for k, v in P1_DEFAULT_KEYBOARD.items()}
            self.p1.pad_bindings = dict(DEFAULT_GAMEPAD)
        else:
            self.p2.key_bindings = {k: list(v) for k, v in P2_DEFAULT_KEYBOARD.items()}
            self.p2.pad_bindings = dict(DEFAULT_GAMEPAD)

INPUT = InputManager()
