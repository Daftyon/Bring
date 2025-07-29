# setup.py
"""
Minimal setup for Bring parser testing.
"""

from setuptools import setup, find_packages

setup(
    name="bring-parser",
    version="1.0.0",
    description="Parser for the Bring file format",
    author="Daftyon Team",
    author_email="contact@daftyon.com",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
