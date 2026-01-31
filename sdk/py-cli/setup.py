from setuptools import setup, find_packages

setup(
    name="originmark-cli",
    version="1.0.0",
    description="CLI tool for OriginMark digital signature verification",
    author="OriginMark",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "pynacl>=1.5.0",
        "requests>=2.31.0",
        "rich>=13.7.0",
        "cryptography>=42.0.0",
        "pydantic>=2.5.3",
        "python-dateutil>=2.8.2",
        "colorama>=0.4.6",
        "tabulate>=0.9.0",
        "toml>=0.10.2",
        "keyring>=24.3.0",
        "secure>=0.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-cov>=4.1.0",
            "black>=24.1.0",
            "isort>=5.13.2",
            "mypy>=1.8.0",
            "flake8>=7.0.0",
        ],
        "security": [
            "bandit>=1.7.5",
            "safety>=3.0.1",
        ]
    },
    entry_points={
        "console_scripts": [
            "originmark=originmark.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Bug Reports": "https://github.com/originmark/originmark/issues",
        "Source": "https://github.com/originmark/originmark",
        "Documentation": "https://docs.originmark.dev",
    },
    zip_safe=False,
) 