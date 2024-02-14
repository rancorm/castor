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

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.addonmanager import Loader

def generate_schema(json_object):
    schema = { "type": "object", "properties": {} }

    # Handle simple types 
    if type(json_object) is not dict and type(json_object) is not list:
       return type(json_object).__name__.lower()

    if type(json_object) is list:
        # Assume that all elements in the array have the same schema
        for item in json_object:
            return generate_schema(item) if item else {}

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
        return "JSON schema", contentviews.format_text(json.dumps(generate_schema(flow.response.json()), indent=2) if flow else {})

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> float:
        if content_type in self.content_types and self.auto_render:
            return 1
        else:
            return 0

class Castor:
    def __init__(self):
        self.schemas = []
        self.output = os.getenv("CASTOR_OUTPUT", None)
        self.checks = os.getenv("CASTOR_CHECKS", 1)

    def _write_schema(self, schema, host, port, path, direction):
        if self.output:
            endpoint_path = path.replace("/", "_")
            file_name = f"{host}_{port}{endpoint_path}.{direction}.json"
            file_path = os.path.join(self.output, file_name)

            ctx.log.info(f"Writing schema to {file_path}")
            #with open(file_path, "w") as file:
            #   json.dump(schema, file, indent=2)

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

        if len(req.content) > 0:
            # Handle requests only with JSON responses
            if resp_type == "application/json" or not self.checks:
                req_type = req.headers.get("Content-Type", None)

                if req_type:
                    if req_type == "application/json" or not self.checks:
                        try:
                            req_json = req.json()
                            req_schema = generate_schema(req_json)
                            req_msg = json.dumps(req_schema, indent=2)

                            msg += "Request:\n" + req_msg

                            if self.output:
                                self._write_schema(req_msg,
                                                req_host,
                                                req_port,
                                                req_path,
                                                "req")
                        except json.JSONDecodeError:
                            ctx.log.error("Failed to parse JSON request")
                    else:
                        # Not JSON request content type, try JSON decode, use text if that fails
                        try:
                            req_json = req.json()
                            req_schema = generate_schema(req_json)
                            req_msg = json.dumps(req_schema, indent=2)
                        except json.JSONDecodeError:
                            ctx.log.error("Failed to parse JSON request, using text instead")

                            req_msg = req.get_text()

                        if req_msg:
                            msg += "Request:\n" + req_msg

                            if self.output:
                                self._write_schema(req_msg,
                                                req_host,
                                                req_port,
                                                req_path,
                                                "req")
                else:
                    ctx.log.error("No content type in request")

                    # No content type, attempt JSON decode, output text if fails
                    try:
                        req_json = req.json()
                        req_schema = generate_schema(req_json)
                        req_msg = json.dumps(req_schema, indent=2)
                    except json.JSONDecodeError:
                        ctx.log.error("Failed to parse JSON request, using text instead")

                        req_msg = req.get_text()

                    if req_msg:
                        msg += "Request:\n" + req_msg
                        
                        if self.output:
                            self._write_schema(req_msg,
                                            req_host,
                                            req_port,
                                            req_path,
                                            "req")

                # Log request
                if msg:
                    ctx.log.info(msg)

        # Handle JSON responses
        if resp_type == "application/json" or not self.checks:
            try:
                resp_json = resp.json()

                if type(resp_json) is dict:
                    resp_schema = generate_schema(resp_json)
                    resp_msg = json.dumps(resp_schema, indent=2)
               
                    if resp_msg:
                        ctx.log.info("Response:\n" + resp_msg)

                    if self.output:
                        self._write_schema(resp_msg,
                                           req_host,
                                           req_port,
                                           req_path,
                                           "resp")
            except json.JSONDecodeError:
                ctx.log.error("Failed to parse JSON response")

                return

view = CastorContentView()
addons = [Castor()]

def load(loader: Loader):
    contentviews.add(view)

def done():
    contentviews.remove(view)
