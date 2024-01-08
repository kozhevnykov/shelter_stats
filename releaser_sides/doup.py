import keyboard, time
prev_time = 0

def duplicate_key(event):
    global prev_time
    if event.event_type == keyboard.KEY_DOWN:
        cur_time = time.time_ns() / 1000000000
        print(cur_time - prev_time, "pressed : ", event.name)
        prev_time = cur_time

    if event.event_type == keyboard.KEY_UP:
        cur_time = time.time_ns() / 1000000000
        print(cur_time - prev_time, "released : ", event.name)
        prev_time = cur_time
    # if event.event_type == keyboard.KEY_DOWN and event.name == 'z':
    #     time.sleep(0.03)
    #     keyboard.release('z')
    if event.event_type == keyboard.KEY_DOWN and event.name == 's':
        time.sleep(0.05)
        keyboard.release('s')
        cur_time = time.time_ns() / 1000000000
        print(cur_time - prev_time, "AUTO release S")
        prev_time = cur_time

    # elif event.event_type == keyboard.KEY_UP and event.name == 'w':
    #     time.sleep(0.02)
    #     keyboard.press('w')
    #     time.sleep(0.08)
    #     keyboard.release('w')
    #
    # if event.event_type == keyboard.KEY_DOWN and event.name == 'e':
    #     time.sleep(0.03)
    #     keyboard.release('e')
    #     time.sleep(0.007)
    #     keyboard.press('e')


print('Started,\nPress "]" to stop')

keyboard.hook(duplicate_key)
keyboard.wait(']')
print('stopped')