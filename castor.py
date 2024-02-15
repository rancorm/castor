"""
JSON schema mitmproxy addon.

Run as follows:
    mitmproxy -s castor.py
or 
    mitmweb -s castor.py

Set environment variable CASTOR_AUTO_RENDER=1 to enable automatic rendering of JSON schemas.
Set environment variable CASTOR_CHECKS=0 to disable request/response content type checks.
Set environment variable CASTOR_OUTPUT=/path/to/json/schemas/ to enable output to file system.
"""
import json
import os
import time

from enum import Enum

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.addonmanager import Loader

def generate_schema_text(json_object):
    return json.dumps(json_object, indent=2)

def generate_schema(json_object):
    schema = { "type": "object", "properties": {} }

    # Handle simple types 
    if type(json_object) is not dict and type(json_object) is not list:
       return type(json_object).__name__.lower()

    # Handle arrays
    if type(json_object) is list:
        return [generate_schema(item) for item in json_object]

    # Generate schema for each key in the JSON object
    for key, value in json_object.items():
        if isinstance(value, dict):
            # Recursively generate schema for nested objects
            schema["properties"][key] = generate_schema(value)
        elif isinstance(value, list):
            # Handle arrays
            if value:
                # Assume that all elements in the array have the same schema
                schema["properties"][key] = {
                    "type": "array",
                    "items": generate_schema(value[0]) if value else {}
                }
            else:
                # Empty array, no specific items schema
                schema["properties"][key] = { "type": "array" }
        else:
            # Simple type
            schema["properties"][key] = { "type": type(value).__name__.lower() }

    return schema

class CastorContentView(contentviews.View):
    name = "json-schema"
    content_types = [ "application/json" ]
    auto_render = os.getenv("CASTOR_AUTO_RENDER", 0)

    def __call__(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> contentviews.TViewResult:
        return "JSON schema", contentviews.format_text(generate_schema_text(flow.response.json()) if flow else {})

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> float:
        if not data:
            return 0.0

        if content_type in self.content_types and self.auto_render:
            return 1.0
        else:
            return 0.0

class CastorType(Enum):
    REQUEST = "req"
    RESPONSE = "resp"

class Castor:
    def __init__(self):
        self.schemas = []
        self.output = os.getenv("CASTOR_OUTPUT", None)
        self.checks = os.getenv("CASTOR_CHECKS", 1)
    
    def _write_schema(self, schema, host, port, path, direction: CastorType):
        endpoint_path = path.replace("/", "_")
        current_time = time.time()
        file_name = f"{host}_{port}.{current_time}.{direction.value}.json"
        file_path = os.path.join(self.output, file_name)

        ctx.log.info(f"Writing schema to {file_path}")

        with open(file_path, "w") as file:
            json.dump(schema, file, indent=2)

    def response(self, flow):
        # Flow request
        req = flow.request
        req_method = req.method
        req_host = req.host
        req_port = req.port
        req_path = req.path
        req_version = req.http_version

        # Flow response
        resp = flow.response
        resp_code = resp.status_code
        resp_type = resp.headers.get("Content-Type", None)
        
        msg = f""

        if req.content and len(req.content) > 0:
            # Handle requests only with JSON responses, or all requests if checks are disabled
            if resp_type == "application/json" or not self.checks:
                req_type = req.headers.get("Content-Type", None)

                if req_type:
                    if req_type == "application/json" or not self.checks:
                        try:
                            req_json = req.json()
                            req_schema = generate_schema(req_json)
                            req_msg = generate_schema_text(req_schema)

                            msg += "Request:\n" + req_msg

                            if self.output:
                                self._write_schema(req_schema,
                                                req_host,
                                                req_port,
                                                req_path,
                                                CastorType.REQUEST)
                        except json.JSONDecodeError:
                            ctx.log.error("Failed to parse JSON request")
                    else:
                        # Not JSON request content type, try JSON decode, use text if that fails
                        try:
                            req_json = req.json()
                            req_schema = generate_schema(req_json)
                            req_msg = generate_schema_text(req_schema)
                        except json.JSONDecodeError:
                            ctx.log.error("Failed to parse JSON request, using text instead")

                            req_msg = req.get_text()

                        if req_msg:
                            msg += "Request:\n" + req_msg

                            if self.output:
                                self._write_schema(req_schema,
                                                req_host,
                                                req_port,
                                                req_path,
                                                CastorType.REQUEST)
                else:
                    ctx.log.info("No content type in request")

                    # No content type, attempt JSON decode, output text if fails
                    try:
                        req_json = req.json()
                        req_schema = generate_schema(req_json)
                        req_msg = generate_schema_text(req_schema)
                    except json.JSONDecodeError:
                        ctx.log.error("Failed to parse JSON request, using text instead")

                        req_msg = req.get_text()

                    if req_msg:
                        msg += "Request:\n" + req_msg
                        
                        if self.output:
                            self._write_schema(req_schema,
                                            req_host,
                                            req_port,
                                            req_path,
                                            CastorType.REQUEST)

                # Log request
                if msg:
                    ctx.log.info(msg)
 
        # Write request URI to file system, if output is enabled, and response is JSON
        # or checks are disabled.
        if self.output and resp_type == "application/json" or not self.checks:
            current_time = time.time()
            file_name = f"{req_host}_{req_port}.{current_time}.req-uri"
            file_path = os.path.join(self.output, file_name)

            ctx.log.info(f"Writing request URI to {file_path}")

            with open(file_path, "w") as file:
                file.write(f"{req_method} {req_path} {req_version}")

        # Handle JSON responses
        if resp_type == "application/json" or not self.checks:
            try:
                resp_json = resp.json()

                if type(resp_json) is dict:
                    resp_schema = generate_schema(resp_json)
                    resp_msg = generate_schema_text(resp_schema)

                    if resp_msg:
                        ctx.log.info("Response:\n" + resp_msg)

                    if self.output:
                        self._write_schema(resp_schema,
                                           req_host,
                                           req_port,
                                           req_path,
                                           CastorType.RESPONSE)
            except json.JSONDecodeError:
                ctx.log.error("Failed to parse JSON response")

                return

addons = [Castor()]
view = CastorContentView()

def load(loader: Loader):
    contentviews.add(view)

    ctx.log.info("Options:")
    ctx.log.info(f"  auto_render={view.auto_render}")
    ctx.log.info(f"  checks={addons[0].checks}")
    ctx.log.info(f"  output={addons[0].output}")
    ctx.log.info("Castor loaded")

def done():
    contentviews.remove(view)
