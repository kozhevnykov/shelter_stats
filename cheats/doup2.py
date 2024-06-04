import keyboard, time

def duplicate_key(event):
    if event.event_type == keyboard.KEY_DOWN and event.name == 'z':
        time.sleep(0.03)
        keyboard.release('z')
    if event.event_type == keyboard.KEY_DOWN and event.name == 's':
        time.sleep(0.05)
        keyboard.release('s')

print('Started, \nPress "]" to stop')
keyboard.hook(duplicate_key)
keyboard.wait(']')
print('stopped')
