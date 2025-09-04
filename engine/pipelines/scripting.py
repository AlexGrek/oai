# This script defines a Python class that encapsulates the
# py_mini_racer JavaScript engine, providing a safe and high-level
# API for processing text and executing user-defined scripts.

import json
import re
from typing import Any
from py_mini_racer import MiniRacer


class ScriptingError(Exception):
    """Custom exception for errors originating from the JS script."""

    pass


class SafeScriptingEngine:
    """
    A class that provides a safe and isolated JavaScript scripting environment.
    It hides the py_mini_racer implementation and reuses a single context.
    """

    def __init__(self):
        self._ctx = MiniRacer()
        self._initialize_context()

    def _initialize_context(self):
        """Initializes the MiniRacer context with essential helper functions."""
        # This script defines a simple JSONPath-like function to be used by extract_json.
        # This is a safe alternative to embedding a complex library.
        js_helpers = """
        // Helper to safely extract a JSON object from a string.
        function extractJson(text) {
            const match = text.match(/```json\\s*([\\s\\S]*?)\\s*```/);
            if (match && match[1]) {
                return match[1].trim();
            }
            return null;
        }

        // Helper to provide simple pathing (like jq or jsonpath).
        // This is a basic implementation for demonstration purposes.
        function findInJson(data, path) {
            let parts = path.split('.');
            let current = data;
            for (let i = 0; i < parts.length; i++) {
                let part = parts[i];
                if (Array.isArray(current)) {
                    // Handle array indices and simple filtering
                    if (part.startsWith('[') && part.endsWith(']')) {
                        const index = parseInt(part.slice(1, -1));
                        if (!isNaN(index) && index < current.length) {
                            current = current[index];
                            continue;
                        }
                    }
                    return null; // Path part is not a valid array index
                } else if (typeof current === 'object' && current !== null) {
                    current = current[part];
                } else {
                    return null; // Current element is not an object.
                }
            }
            return current;
        }
        """
        self._ctx.eval(js_helpers)

    def reset_context(self):
        """Resets the scripting context, clearing any state."""
        self._ctx = MiniRacer()
        self._initialize_context()

    def extract_json(self, text: str, jsonpath_expr: str) -> Any:
        """
        Extracts a JSON object from text and returns a value from a JSON path.

        Args:
            text (str): The input string containing a JSON object.
            jsonpath_expr (str): A simple dot-separated path (e.g., 'report.status').

        Returns:
            any: The value found at the specified path, or None if not found.
        """
        # Execute the extraction and lookup logic in the sandbox.
        # We now correctly escape the f-string braces.
        js_code = f"""
        const text_input = {json.dumps(text)};
        const jsonString = extractJson(text_input);
        if (jsonString) {{
            const data = JSON.parse(jsonString);
            const result = findInJson(data, '{jsonpath_expr}');
            return JSON.stringify({{ result }});
        }} else {{
            return JSON.stringify({{ result: null }});
        }}
        """
        try:
            result_json = self._ctx.eval(js_code)
            result_dict = json.loads(result_json)
            return result_dict["result"]
        except Exception as e:
            raise ScriptingError(f"JSON extraction failed: {e}")

    def extract_script(self, text: str, script_body: str) -> Any:
        """
        Executes a user-defined JavaScript function body in the sandbox.

        Args:
            text (str): The input string to be passed to the function.
            script_body (str): The body of the function to execute.

        Returns:
            any: The return value of the JavaScript function.

        Raises:
            ScriptingError: If the JavaScript code contains an error.
        """
        # Wrap the user's code in a full function definition.
        wrapped_script = f"""
        function processInput(text) {{
            {script_body}
        }}
        """
        try:
            # First, evaluate the function definition in the context.
            self._ctx.eval(wrapped_script)

            # Then, call the function and get the result.
            # We use json.dumps() to safely pass the Python string as a JS string literal.
            js_call_string = f"JSON.stringify(processInput({json.dumps(text)}));"
            result_json_string = self._ctx.eval(js_call_string)

            # Return the result as a Python object.
            return json.loads(result_json_string)

        except Exception as e:
            # Wrap the JavaScript error in a custom Python exception.
            raise ScriptingError(f"Script execution failed: {e}")
