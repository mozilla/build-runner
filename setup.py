from setuptools import setup

setup(
    name="runner",
    version="0.0.0",
    description="Task runner",
    author="Chris AtLee",
    author_email="chris@atlee.ca",
    packages=[
        "runner",
        "runner.lib"
    ],
    entry_points={
        "console_scripts": ["runner = runner:main"],
    },
    url="https://github.com/mozilla/runner",
    setup_requires=["nose==1.3.1"],
)
