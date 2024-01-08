import keyboard, time
import random

keys = ['i','j','k','l']
status = False

def get_direction(k):
    keys = ['i', 'j', 'k', 'l']
    if k == 'i':
        return 0
    elif k == 'j':
        return 1
    elif k == 'k':
        return 2
    elif k == 'l':
        return 3
    else:
        return -1

def duplicate_key(event):
    global status
    if event.event_type == keyboard.KEY_DOWN and event.name in keys:
        if status:
            randint = random.randint(0, 3)
            keyboard.press(keys[randint])
            time.sleep(0.01)
            keyboard.release(keys[randint])
        status = False

    if event.event_type == keyboard.KEY_UP and event.name in keys:
        status = True


print('Started,\nPress "]" to stop')

keyboard.hook(duplicate_key)
keyboard.wait(']')
print('stopped')