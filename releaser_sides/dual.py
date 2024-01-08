import pygame
import keyboard, time



if __name__ == '__main__':
    pygame.init()
    pygame.joystick.init()
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Name: {joy.get_name()} | Buttons: {joy.get_numbuttons()} | Axes: {joy.get_numaxes()}")

    directs = ['u','j','h','k']

    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN and event.button == 2:
                keyboard.press('x')
            if event.type == pygame.JOYBUTTONUP and event.button == 2:
                keyboard.release('x')

            if event.type == pygame.JOYBUTTONDOWN and 11 <= event.button <= 14:
                keyboard.press(directs[event.button - 11])
            if event.type == pygame.JOYBUTTONUP and 11 <= event.button <= 14:
                keyboard.release(directs[event.button - 11])