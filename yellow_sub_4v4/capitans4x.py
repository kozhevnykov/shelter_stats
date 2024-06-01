import json
import os
import pandas as pd

res = []
print(len(os.listdir("../dataHAX/storage/")))
for file in os.listdir("../dataHAX/storage/"):

    with open("../dataHAX/storage/" + file) as f:
        data = json.load(f)
    res.append(data)
print(len(res))

df = pd.DataFrame(res).sort_values(by=['wins'], ascending=False).drop(columns=['playtime'])
df.to_csv("../dataHAX/yes4x4 15 may 2024.csv", index=False)
