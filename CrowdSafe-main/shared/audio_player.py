import os
import time
import threading

class SirenPlayer:
    def __init__(self):
        from config.settings import SIREN_SOUND_PATH
        self.siren_path = SIREN_SOUND_PATH
        self.is_playing = False
        
        # Initialize pygame mixer safely
        try:
            import pygame
            pygame.mixer.init()
            if os.path.exists(self.siren_path):
                self.siren_sound = pygame.mixer.Sound(self.siren_path)
            else:
                self.siren_sound = None
                print(f"Siren file not found at {self.siren_path}. Please add a siren.mp3")
        except ImportError:
            print("Pygame not installed.")
            self.siren_sound = None
        except Exception as e:
            print(f"Audio init error: {e}")
            self.siren_sound = None

    def play(self):
        if not self.is_playing and self.siren_sound:
            self.is_playing = True
            self.siren_sound.play(loops=-1) # loop forever

    def stop(self):
        if self.is_playing and self.siren_sound:
            self.is_playing = False
            self.siren_sound.stop()
