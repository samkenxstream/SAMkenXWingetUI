import sys
import json
import os
import glob
import hashlib
import time

root_dir = os.path.join(os.path.dirname(__file__), "..")
os.chdir(root_dir) # move to root project

if not "--buildfiles" in sys.argv:
    sys.path.append("wingetui")
    os.chdir("wingetui")
else:
    sys.path.append("wingetui_bin")
    os.chdir("wingetui_bin")

HASHES: dict[str:str] = {}

time0 = time.time()

for file in glob.glob("./**/**.py") + glob.glob("./**.py") + glob.glob("./components/**.exe") + glob.glob("./**/**.pyc") + glob.glob("./**.pyc"):
    if "__init__" in file or "__pycache__" in file:
        continue
    with open(file,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        HASHES[file] = readable_hash
        
print(f"Elapsed {time.time()-time0} seconds")

parsed_dict = "HASHES: dict[str:str] = " + json.dumps(HASHES, indent=4)
savable_content = ""

for line in parsed_dict.split("\n"):
    savable_content += "    "+line+"\n"

with open("__init__.py", "r+", encoding="utf-8") as f:
    skip = False
    data = ""
    for line in f.readlines():
        if "BEGIN AUTOGENERATED HASH DICTIONARY" in line:
            data += f'{line}{savable_content}'
            print("  Text modified")
            skip = True
        elif "END AUTOGENERATED HASH DICTIONARY" in line:
            skip = False
        if not skip:
            data += line
    f.seek(0)
    f.write(data)
    f.truncate()
os.system("pause")
