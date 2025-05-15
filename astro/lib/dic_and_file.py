import os


def make_dir(path):
    folders = []
    while not os.path.isdir(path):
        path, suffix = os.path.split(path)
        folders.append(suffix)
    for folder in folders[::-1]:
        path = os.path.join(path, folder)
        os.mkdir(path)
def make_file(path):
    file = os.path.exists(path)
    if not file:
        suffix, filename = os.path.split(path)
        make_dir(suffix)
        os.mknod(path)
        
def find_address(path) -> str:
    while True:
        name = os.path.basename(path)

        if name.startswith("0x"):
            return name

        if name == "":
            return "0x000000"

        path = os.path.dirname(path)