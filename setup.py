from setuptools import find_packages, setup

with open("README.md", "r") as readme:
  long_description = readme.read()

setup(
  name="pybootp",
  version="0.0.1",
  description="Bootstrap protocol python library",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/StidOfficial/pybootp",
  packages=["pybootp"],
)