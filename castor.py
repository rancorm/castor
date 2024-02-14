"""
JSON schema mitmproxy addon.

Run as follows:
    mitmproxy -s castor.py
or 
    mitmweb -s castor.py
"""
import logging
import json

class Castor:
    def __init__(self):
        self.schemas = []

    def _generate_schema(self, json_object):
        schema = { "type": "object", "properties": {} }

        # Handle simple types 
        if type(json_object) is not dict:
            schema["properties"]["type"] = type(json_object).__name__.lower()

            return schema

        # Generate schema for each key in the JSON object
        for key, value in json_object.items():
            if isinstance(value, dict):
                # Recursively generate schema for nested objects
                schema["properties"][key] = self._generate_schema(value)
            elif isinstance(value, list):
                # Handle arrays
                if value:
                    # Assume that all elements in the array have the same schema
                    schema["properties"][key] = {
                        "type": "array",
                        "items": self._generate_schema(value[0]) if value else {}
                    }
                else:
                    # Empty array, no specific items schema
                    schema["properties"][key] = { "type": "array" }
            else:
                # Simple type
                schema["properties"][key] = { "type": type(value).__name__.lower() }

        return schema

    def response(self, flow):
        req = flow.request
        req_method = req.method
        req_host = req.host
        req_port = req.port
        resp = flow.response
        resp_code = resp.status_code
        resp_type = resp.headers.get("Content-Type", None)
    
        msg = f"{req_method} to {req_host}:{req_port}"

        if resp_type == "application/json":
            req_type = req.headers.get("Content-Type", None)

            if req_type:
                msg += f" ({req_type})"

                if req_type == "application/json":
                    try:
                        req_json = req.json()
                        req_schema = self._generate_schema(req_json)
                        req_msg = json.dumps(req_schema, indent=2)

                        msg += "\n" + req_msg
                    except json.JSONDecodeError:
                        logging.error("Failed to parse JSON request")
            else:
                req_text = req.get_text()

                if req_text:
                    msg += "\n" + req_text
    
        # Log request and text
        logging.info(msg)

        msg = f"{resp_code} from {req_host}:{req_port}"
        
        if resp_type:
            msg += f" ({resp_type})"
 
        # Log response and JSON
        logging.info(msg)

        # Handle JSON responses
        if resp_type == "application/json":
            try:
                resp_json = resp.json()

                if type(resp_json) is dict:
                    resp_schema = self._generate_schema(resp_json)
                    resp_msg = json.dumps(resp_schema, indent=2)
                
                    logging.info("\n" + resp_msg)
            except json.JSONDecodeError:
                logging.error("Failed to parse JSON response")

                return

addons = [Castor()]
