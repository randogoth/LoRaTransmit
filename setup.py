import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="loratransmit",
    version="0.3.2",
    author="randogoth",
    author_email="randogoth@posteo.org",
    description="LoRa packet transmitter for RNode hardware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/randogoth/loratransmit",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points= {
        'console_scripts': ['loratransmit=loratransmit:main']
    },
    install_requires=['pyserial'],
    python_requires='>=3.6',
)