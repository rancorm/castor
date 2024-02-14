# Castor

<p align="center">
    <img src="https://raw.githubusercontent.com/rancorm/castor/main/beaver.png" width="200" height="200" alt="Castor logo" />
</p>

Image is sourced from [pngimg](https://pngimg.com/image/31353).

mitmproxy add-on that captures JSON schemas.

## Start here

Clone this repository.

```
git clone https://github.com/rancorm/castor.git
cd castor
```

Make Python virtual environment, install dependencies, and run.

```
python -m venv .venv
pip install -r requirements.txt
```

Run `mitmproxy` or `mitmweb` with the add-on script `castor.py`.

```
mitmproxy -s ./castor.py
```

```
mitmweb -s ./castor.py --no-web-open-browser
```

## Output


## Options

Disable checks of content type, set `CASTOR_CHECKS` to `0`. To disable the
auto rendering of JSON to JSON schema, set `CASTOR_AUTO_RENDER` to `1`.

## Saving to disk

To save generated schema to disk, set `CASTOR_OUTPUT` to the path for saving.

```
export CASTOR_OUTPUT=/mnt/data
```

This can perticularly be useful with persisent storage volumes.
