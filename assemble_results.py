import json
import os
import shutil
import sys
import pandas as pd

def flatten(x, sep='.'):
    obj = {}
    def recurse(t, parent_key=''):
        if isinstance(t, list):
            for i, ti in enumerate(t):
                recurse(ti, f'{parent_key}{sep}{i}' if parent_key else str(i))
        elif isinstance(t, dict):
            for k, v in t.items():
                recurse(v, f'{parent_key}{sep}{k}' if parent_key else k)
        else:
            obj[parent_key] = t

    recurse(x)
    return obj

data = []

for model in os.listdir("drl_robot"):
    r = {}
    r['filename'] = str(model)
    model_path = os.path.join("drl_robot",model)
    for name in ['params','average_scores']:
        file_path = os.path.join(model_path,f'{name}.json')
        try:
            with open(file_path,'r') as fp:
                r.update(flatten(json.load(fp)))
        except (FileNotFoundError, KeyError) as e:
            print(str(e))

    data.append(r)

csv_file_path = os.path.join('results.csv')
df = pd.DataFrame(data)
df.to_csv(csv_file_path, index=False)