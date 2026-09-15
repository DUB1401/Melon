# Melon

![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)
![Python version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fotaku-melons%2Fmelon%2Frefs%2Fheads%2Fmain%2Fpyproject.toml
)

Management system for manga and ranobe parsers modules capable of retrieving titles information, saving it in JSON, requesting updates and compiling content into an easy-to-read format.

<p align="center">
	<img src="icon.svg" width=25% height=25% allign="center">
</p>

We welcome all developers and enthusiasts!

Documentation available in [this](https://github.com/otaku-melons/docs) repository and see our [roadmap](https://github.com/orgs/otaku-melons/projects/1/views/1) for information about development progress.

> [!NOTE]  
> _We respect the intellectual property of content providers and do not provide any solutions designed to bypass paywalls or illegally access premium content. To minimize the load on these resources, a brief delay is enforced between requests._

## Getting started
1. Install [uv](https://docs.astral.sh/uv/) project manager on your system.
2. Create virtual enviroment and install Melon.
```
uv venv
uv pip install git+https://github.com/otaku-melons/melon
uv venv .venv --prompt melon
```
3. Activate virtual enviroment and run Melon.
```Bash
source .venv/bin/activated
melon help && pxm help && urun help
```
4. Add Git-repository of parser.
```
pxm remotes add https://github.com/otaku-melons/{PARSER}
```
5. Install parser and configure it by editing settings file in configs directory.
```
pxm install {PARSER}
```
6. Parse title for creation descriptive JSON file in output directory.
```
melon parse {SLUG} --use {PARSER}
```
6. Build read-ready content from descriptive JSON file.
```Bash
melon build manga {FILE} --use {PARSER} -cbz
```

_Copyright © DUB1401. 2024-2026._
