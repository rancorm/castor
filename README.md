# Castor

<p align="center">
    <img src="https://raw.githubusercontent.com/rancorm/castor/main/beaver.png" width="200" height="200" alt="Castor logo" />
</p>

Image is sourced from [pngimg](https://pngimg.com/image/31353).

mitmproxy add-on that captures JSON schemas.

## Start here

Clone this repository.

```sh
git clone https://github.com/rancorm/castor.git
cd castor
```

Make Python virtual environment, install dependencies, and run.

```sh
python -m venv .venv
pip install -r requirements.txt
```

Run `mitmproxy` terminal UI, `mitmdump` or `mitmweb` with the add-on script `castor.py`.

```sh
mitmproxy -s ./castor.py
```

Run with web server UI.

```sh
mitmweb -s ./castor.py
```

On the Flow > Response tab, change **View** to `json-schema`, or
set the `CASTOR_AUTO_RENDER` to `1` to auto render JSON resquest and responses
to JSON schemas.

Dump to the console with `mitmdump`.

```sh
mitmdump -s ./castor.py
```

## Output

Example output from `mitmdump` generated JSON schema.

```json
{
  "type": "object",
  "properties": {
    "Code": {
      "type": "int"
    },
    "CalendarModelEventID": {
      "type": "str",
      "pattern": "uri"
    },
    "Refresh": {
      "type": "int"
    },
    "More": {
      "type": "int"
    }
  }
}
```

## Options

Disable checks of content type, set `CASTOR_CHECKS` to `0`. To disable the
auto rendering of JSON to JSON schema, set `CASTOR_AUTO_RENDER` to `1`.

## Saving to disk

To save generated schema to disk, set `CASTOR_OUTPUT` to the path for saving.

```sh
export CASTOR_OUTPUT=/mnt/data
```

This can perticularly be useful with persisent storage volumes inside containers.
