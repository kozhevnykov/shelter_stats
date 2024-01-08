import json
import os
import pandas as pd

res = []
print(len(os.listdir("../dataHAX/storage 2/")))
for file in os.listdir("../dataHAX/storage 2/"):

    with open("../dataHAX/storage 2/" + file) as f:
        data = json.load(f)
    res.append(data)
print(len(res))

df = pd.DataFrame(res).sort_values(by=['wins'], ascending=False).drop(columns=['playtime'])
df.to_csv("../dataHAX/yes4x4 26 dec 2023.csv", index=False)
