from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='rpi_intercom',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
    packages=find_packages(include=['rpi_intercom']),
    package_data = {
        'rpi_intercom': ['static/*']
    },
    version='0.0.17',
    description='Intercom library for a raspberrypi',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["pymumble", "pyalsaaudio", "gpiozero", "schema", "pyyaml", "pyOpenSSL", "numpy", "psutil", "aiohttp", "colorlog", "samplerate", "aiorun"],
    author="Stephen Beechen",
    author_email="stephen@beechens.com",
    python_requires=">=3.9",
    license='FUCKING FREE',
)