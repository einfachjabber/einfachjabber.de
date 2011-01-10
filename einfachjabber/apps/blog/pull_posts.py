from git import Repo
from os import path

POSTS = path.join(path.abspath(path.dirname(__file__)), '_posts/')

def pull_posts():
    repo = Repo(POSTS)
    out = repo.remotes.origin.pull()

if __name__ == '__main__':
    pull_posts()
