import pyautogui
import keyboard
import time

move_distance = 60

initial_x, initial_y = -430, 929
x, y = initial_x, initial_y

while True:
    x, y = initial_x, initial_y

    if keyboard.is_pressed('D'):
        x = initial_x - move_distance
    if keyboard.is_pressed('G'):
        x = initial_x + move_distance
    if keyboard.is_pressed('R'):
        y = initial_y - move_distance
    if keyboard.is_pressed('F'):
        y = initial_y + move_distance
    if keyboard.is_pressed('q'):
        break
    pyautogui.moveTo(x, y)

    # print(pyautogui.position())
    # time.sleep(0.5)