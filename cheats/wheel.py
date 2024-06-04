from pynput import mouse, keyboard
import time

keyboard_controller = keyboard.Controller()
key_to_press = keyboard.KeyCode.from_char('x')

def press_key():
    keyboard_controller.press(key_to_press)
    time.sleep(0.03)
    keyboard_controller.release(key_to_press)

# Define the function to handle mouse scroll events
def on_scroll(x, y, dx, dy):

    print(x, y, dx, dy)
    # Check if the scroll count exceeds a threshold
    if dy > 1:
        keyboard_controller.press(key_to_press)
        time.sleep(0.03)
        keyboard_controller.release(key_to_press)
    elif dy == 1:
        keyboard_controller.press(key_to_press)
    elif dy < 0:
        keyboard_controller.release(key_to_press)


with mouse.Listener(on_scroll=on_scroll) as listener:
    listener.join()