import pygame
from typing import Dict, Set
from config.controls import KEYBOARD_CONTROLS, GAMEPAD_CONTROLS

class InputManager:
    """Handles keyboard and gamepad inputs seamlessly."""
    def __init__(self):
        self.keys_pressed: Set[int] = set()
        self.keys_just_pressed: Set[int] = set()
        self.keys_just_released: Set[int] = set()
        
        self.joystick = None
        self.pad_buttons_pressed: Set[int] = set()
        self.pad_buttons_just_pressed: Set[int] = set()
        
    def init(self):
        """Initializes the joystick if available. Must be called after pygame.init()"""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            
    def clear(self):
        """Resets all input states, useful on scene transitions."""
        self.keys_pressed.clear()
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()
        self.pad_buttons_pressed.clear()
        self.pad_buttons_just_pressed.clear()
        
    def update(self):
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()
        self.pad_buttons_just_pressed.clear()

    def process_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            self.keys_pressed.add(event.key)
            self.keys_just_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            if event.key in self.keys_pressed:
                self.keys_pressed.remove(event.key)
            self.keys_just_released.add(event.key)
            
        elif event.type == pygame.JOYBUTTONDOWN:
            self.pad_buttons_pressed.add(event.button)
            self.pad_buttons_just_pressed.add(event.button)
        elif event.type == pygame.JOYBUTTONUP:
            if event.button in self.pad_buttons_pressed:
                self.pad_buttons_pressed.remove(event.button)

    def is_action_pressed(self, action: str) -> bool:
        """Returns True if the action is currently being held down."""
        # Use real-time keyboard state to prevent keys getting stuck across transitions
        keys = pygame.key.get_pressed()
        if action in KEYBOARD_CONTROLS:
            for key in KEYBOARD_CONTROLS[action]:
                if key < len(keys) and keys[key]:
                    return True
                if key in self.keys_pressed:
                    return True
        
        # Check Gamepad Buttons
        if self.joystick and action in GAMEPAD_CONTROLS:
            val = GAMEPAD_CONTROLS[action]
            if isinstance(val, int):
                if val in self.pad_buttons_pressed:
                    return True
                    
        return False

    def is_action_just_pressed(self, action: str) -> bool:
        """Returns True only on the frame the action was pressed."""
        if action in KEYBOARD_CONTROLS:
            for key in KEYBOARD_CONTROLS[action]:
                if key in self.keys_just_pressed:
                    return True
                    
        if self.joystick and action in GAMEPAD_CONTROLS:
            val = GAMEPAD_CONTROLS[action]
            if isinstance(val, int):
                if val in self.pad_buttons_just_pressed:
                    return True
                    
        return False

    def get_axis(self) -> pygame.math.Vector2:
        """Returns a normalized vector representing movement input."""
        axis = pygame.math.Vector2(0, 0)
        
        if self.is_action_pressed('LEFT'): axis.x -= 1
        if self.is_action_pressed('RIGHT'): axis.x += 1
        if self.is_action_pressed('UP'): axis.y -= 1
        if self.is_action_pressed('DOWN'): axis.y += 1
        
        # Override with Gamepad D-pad if active
        if self.joystick:
            hat = self.joystick.get_hat(0)
            if hat != (0, 0):
                axis.x = hat[0]
                axis.y = -hat[1] # Pygame hat Y is inverted compared to screen coords
                
        if axis.length() > 0:
            axis = axis.normalize()
            
        return axis

# Global Input Manager
INPUT = InputManager()
