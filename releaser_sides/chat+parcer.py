import os, re

chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : .*")
not_chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : 💬 .*")
folder = '../vps-logs--ua-1-1--2/hax/out'
for filename in [f for f in sorted(os.listdir(folder)) if f == 'out__2023-']:
    f = os.path.join(folder, filename)
    if filename == '.DS_Store':
        continue
    with open(f, 'r', encoding='utf-8') as file:
        for line in file:
            if chatline.match(line) and not not_chatline.match(line):
                print(line, end='')