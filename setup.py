import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pazgui", # Replace with your own username
    version="0.0.1",
    author="Okan Demir",
    author_email="okndemir@gmail.com",
    description="Python terminal GUI toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dmrokan/pazgui",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.8",
    install_requires=[
       'blessed', 'schedule',
    ],
)

