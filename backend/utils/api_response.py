from flask import jsonify
import os
import traceback

def success_response(message, data=None, status_code=200):
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def error_response(message, error=None, status_code=400):
    response = {"success": False, "message": message}
    
    # Only include error details in development mode
    if error and os.environ.get("FLASK_ENV") == "development":
        response["error"] = str(error)
        traceback.print_exc()
    
    return jsonify(response), status_code