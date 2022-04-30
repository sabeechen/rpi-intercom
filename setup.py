from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='rpi-intercom',
    packages=find_packages(include=['rpi-intercom']),
    ackage_data={'rpi-intercom': ['data/rpi-intercom.service']},
    version='0.0.2',
    description='Intercom library for a raspberrypi',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["pymumble", "pyaudio", "gpiozero", "schema", "pyyaml", "pyOpenSSL", "numpy"],
    author="Stephen Beechen",
    author_email="stephen@beechens.com",
    python_requires=">=3.9",
    license='MIT',
)