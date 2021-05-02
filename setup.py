import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="serenissimo",
    version="0.0.1",
    author="Alberto Granzotto",
    author_email="agranzot@mailbox.org",
    description="A bot to help people in Veneto to find a spot to get vaccinated.",
    install_requires=[
        "requests>=2,<3",
        "beautifulsoup4>=4,<5",
        "pyTelegramBotAPI>=3,<4",
        "python-codicefiscale==0.3.7",
        "python-dotenv==0.17.0",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vrde/serenissimo",
    project_urls={
        "Bug Tracker": "https://github.com/vrde/serenissimo/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: OS Independent",
    ],
    package_data={"": ["*.sql"]},
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.6",
)