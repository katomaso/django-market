# coding:utf-8
import os
from setuptools import setup


def from_requirements(reqname):
    """Extract packages from requirements."""
    with open(reqname, "rt") as reqs:
        return [line.rstrip() for line in reqs]


packages = from_requirements("requirements.txt")

REDISCLOUD_KYES = (
    'REDISCLOUD_URL',
    'REDISCLOUD_PORT',
    'REDISCLOUD_PASSWORD',
)

if all(map(lambda key: key in os.environ, REDISCLOUD_KYES)):
    packages.append('django-redis-cache')
    packages.append('hiredis')

setup(
    name='django-market',
    version='1.0',
    description='Online market where multiple people can sell the same thing',
    author='Tomas Peterka',
    author_email='tomas@peterka.me',
    url='',
    install_requires=packages
)
