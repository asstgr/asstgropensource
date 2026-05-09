from django.shortcuts import render
import json
import requests
from api_management.models import *
import xml.etree.ElementTree as ET
from collections import OrderedDict
from string import Formatter
from urllib.parse import urlencode, quote_plus
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry




def validate_parameters(parameters, user_params, strict=False):
    errors = []
    allowed_names = {param.name for param in parameters}

    for param in parameters:
        if param.required and param.name not in user_params:
            errors.append(f"The required parameter '{param.name}' is missing.")
        # Example of type checking (adapt as needed for your model)
        # if param.expected_type and not isinstance(user_params.get(param.name), param.expected_type):
        #     errors.append(f"The parameter '{param.name}' must be of type {param.expected_type}.")

    if strict:
        for name in user_params:
            if name not in allowed_names:
                errors.append(f"The parameter '{name}' is not recognized for this endpoint.")

    return errors if errors else None



def fill_url_path(path_template, params):
    """
    Replace placeholders {key} in path_template with params[key].
    """
    formatter = Formatter()
    mapping = {}
    for literal_text, field_name, format_spec, conversion in formatter.parse(path_template):
        if field_name is not None:
            # Replace if we have the key, otherwise keep as is
            if field_name in params:
                mapping[field_name] = params[field_name]
            else:
                mapping[field_name] = '{' + field_name + '}'
    return path_template.format(**mapping)


# Function to build the URL with path and query parameters

def build_url(api_url, endpoint_path, parameters, user_params):
    url = api_url.rstrip("/") + "/" + endpoint_path.lstrip("/")  # clean up slashes

    # 1. Replace path parameters
    for param in parameters:
        if param.param_type == 'path':
            if param.name not in user_params:
                raise ValueError(f"Path parameter '{param.name}' is missing.")
            value = quote_plus(str(user_params[param.name]))
            url = url.replace(f"{{{param.name}}}", value)

    # 2. Build query params
    query_params = {
        param.name: user_params.get(param.name, param.default_value)
        for param in parameters
        if param.param_type == 'query' and user_params.get(param.name) is not None
    }

    if query_params:
        connector = '&' if '?' in url else '?'
        url += connector + urlencode(query_params)

    return url

# Function to send the API request


# Global Session (reuses connections)
session = requests.Session()

retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,  # 0.5s, 1s, 2s
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


def send_api_request2(url, method, headers=None, body_params=None, query_params=None):
    method_map = {
        'GET': session.get,
        'POST': session.post,
        'PUT': session.put,
        'DELETE': session.delete,
        'PATCH': session.patch,
    }

    if method not in method_map:
        return None, f"HTTP method not supported: {method}"

    method_function = method_map[method]
    headers = headers or {}
    body_params = body_params or {}
    query_params = query_params or {}

    try:
        timeout = 5  # 🔥 CRUCIAL

        if method == 'GET':
            params_to_use = query_params if query_params else body_params
            response = method_function(
                url,
                headers=headers,
                params=params_to_use if params_to_use else None,
                timeout=timeout
            )

        elif method in ['POST', 'PUT', 'PATCH']:
            response = method_function(
                url,
                headers=headers,
                json=body_params if body_params else None,
                timeout=timeout
            )

        else:
            response = method_function(
                url,
                headers=headers,
                timeout=timeout
            )

        return response, None

    except requests.Timeout:
        return None, "Request timeout"

    except requests.RequestException as e:
        return None, f"HTTP error: {str(e)}"


def send_api_request(url, method, headers, body_params, user_params):
    method_map = {
        'GET': requests.get,
        'POST': requests.post,
        'PUT': requests.put,
        'DELETE': requests.delete,
    }

    if method not in method_map:
        return None, "Method not supported"

    method_function = method_map[method]
    #if method in ['POST', 'PUT']:
        #response = method_function(url, headers=headers, json=body_params if body_params else user_params)
    if method in ['POST', 'PUT'] and body_params:
        json_body = json.dumps(body_params, indent=4, ensure_ascii=False)
        response = method_function(url, headers=headers, data=json_body)  # Use 'data' because it's already a JSON string
    else:
        response = method_function(url, headers=headers)

    return response, None



def build_body_payload(parameters, user_params):
    body = OrderedDict()
    for param in parameters:
        if param.is_in_body:
            value = user_params.get(param.name)
            if param.param_type == 'json':
                try:
                    value = json.loads(value)
                except Exception:
                    pass
            elif param.param_type == 'bool':
                value = value.lower() in ['true', '1', 'yes']
            # Include all is_in_body parameters, applying specific processing if needed
            body[param.name] = value
    return body
# Main optimized view

# Function to handle the session
def handle_session(request):
    request.session.cycle_key()


# Function to retrieve API and Endpoint details
def get_endpoint_details(endpoint):
    methods = Method.objects.filter(endpoint=endpoint)
    parameters = Parameter.objects.filter(endpoint=endpoint).order_by('order')
    headers = Header.objects.filter(endpoint=endpoint)
    return methods, parameters, headers


# Function to process the method chosen by the user
def process_method(request, methods):
    method = request.POST.get('method')
    selected_method = next((m.method for m in methods if m.method == method), None)
    return method, selected_method


# Function to validate and process user parameters
def validate_and_process_parameters(request, parameters):
    """
    Validates and processes the query parameters.
    Properly separates the query, body, and header parameters.
    """
    user_params = {}
    request_data_clean = []
    header_params = {}
    body_params = {}
    query_params = {}  # New: separated query parameters
    error_message = None

    for param in parameters:
        param_value = param.stored_value or request.POST.get(param.name, param.default_value)
        
        # Only process if value exists
        if param_value is not None and param_value != '':
            user_params[param.name] = param_value
            
            if request.POST.get(param.name):
                request_data_clean.append(param_value)
            
            # Classify the parameters according to their type
            if param.is_in_body:
                body_params[param.name] = param_value
            elif param.param_type == 'query':
                query_params[param.name] = param_value
            elif param.param_type == 'header':
                header_params[param.name] = param_value
            elif param.param_type == 'path':
                # The path parameters remain in user_params for fill_url_path
                pass

    # Build the body payload with the existing function
    body_params = build_body_payload(parameters, user_params)
    
    # validate the settings
    validation_error = validate_parameters(parameters, user_params)
    if validation_error:
        error_message = validation_error

    return user_params, request_data_clean, header_params, body_params, query_params, error_message

# Function to prepare request headers
# core/utils.py  (ou api_management/utils.py selon ton projet)

def prepare_headers(headers, api, header_params):
    request_headers = {header.name: header.value for header in headers}
    request_headers.update(header_params)

    if api.auth_required:
        # ── OAuth 2.0 ──────────────────────────────────────────
        if hasattr(api, 'oauth_config'):
            from api_management.oauth_service import OAuthService
            try:
                token = OAuthService.get_valid_token(api.oauth_config)
                request_headers['Authorization'] = f'Bearer {token}'
            except Exception as e:
                raise ValueError(f"OAuth2 token error: {e}")

        # ── API Key classique ───────────────────────────────────
        elif api.api_key_encrypted:
            request_headers['Authorization'] = f'Bearer {api.api_key_encrypted}'

    return request_headers


# Function to call the API


def call_api(url, selected_method, request_headers, body_params, user_params):
    try:
        response, error_message = send_api_request(url, selected_method, request_headers, body_params, user_params)
        if response:
            # Check for HTTP errors
            response.raise_for_status()
        return response, error_message
    except requests.exceptions.RequestException as e:
        error_message = f"Error while calling the API: {str(e)}"
        return None, error_message



def process_api_response(response, display_format, language):
    content_type = response.headers.get('Content-Type', '')

    MAX_RAW_RESPONSE_BYTES = 100_000
    MAX_VERBOSE_CHARS = 20_000

    # 🔒 Security: Raw Size
    if len(response.content) > MAX_RAW_RESPONSE_BYTES:
        return (
            f"[Error] The API response exceeds the maximum allowed size "
            f"({MAX_RAW_RESPONSE_BYTES // 1000} KB)."
        )

    json_response = None
    try:
        json_response = response.json()
    except Exception:
        pass

    if json_response is not None:
        mode_map = {
            'compact': DisplayMode.COMPACT,
            'standard': DisplayMode.STANDARD,
            'verbose': DisplayMode.VERBOSE,
            'flat_text': DisplayMode.STANDARD,
        }

        if display_format in mode_map:
            cleaner = JSONCleaner(display_mode=mode_map[display_format])
            rendered = cleaner.json_to_flat_text(json_response)

            # 🔥 Specific limit for verbose mode
            if display_format == "verbose" and len(rendered) > MAX_VERBOSE_CHARS:
                return (
                    "[Error] The response is too large to be displayed in verbose mode. "
                    "Please use JSON or compact format."
                )

            return rendered

        elif display_format == "json":
            return json.dumps(json_response, indent=4, ensure_ascii=False)

       
        return json.dumps(json_response, indent=4, ensure_ascii=False)

    # XML
    elif 'application/xml' in content_type or 'text/xml' in content_type:
        try:
            xml_root = ET.fromstring(response.text)
            return ET.tostring(xml_root, encoding='unicode', method='xml')
        except Exception:
            return response.text

    # Texte brut
    else:
        return response.text.replace("\n", "<br>")



# Function to log the API call
def log_api_call2(session_id, user_id, api, endpoint, selected_method, request_data_clean, response_data, status_code):
    # If session_id is None, log as "No Session"
    session_id = session_id if session_id else 'No Session'
    
    # Retrieve the user by user_id if provided
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None

    # Log without the API key
    APILog.objects.create(
        session_id=session_id,
        user=user,
        api=api,
        endpoint=endpoint,
        method=selected_method,
        request_data=request_data_clean,
        response_data=response_data,
        status_code=status_code,
        response_size=len(response_data.encode("utf-8")) if isinstance(response_data, str) else 0
    )


# Function to render an error
def render_error(request, api, endpoint, methods, parameters, headers, error_message):
    return render(request, 'execute_api.html', {
        'api': api,
        'endpoint': endpoint,
        'methods': methods,
        'parameters': parameters,
        'headers': headers,
        'error_message': error_message,
    })




class DisplayMode(Enum):
    """Available display modes"""
    COMPACT = "compact"      # Technical, concise version
    STANDARD = "standard"    # Readable with smart formatting
    VERBOSE = "verbose"      # Very detailed with complete sentences

class JSONCleaner:
    def __init__(self, 
                 remove_private_keys=True, 
                 remove_empty_values=True,
                 max_string_length=100,
                 max_array_items=10,
                 indent_size=2,
                 display_mode=DisplayMode.STANDARD,
                 use_emojis=True,
                 humanize_keys=True):
        """
        Enhanced JSON Cleaner Initializer
        
        Args:
            remove_private_keys: Removes keys starting with '_'
            remove_empty_values: Removes blank values (None, "", [], {})
            max_string_length: Max length of strings before truncation
            max_array_items: Max number of items in an array to display
            indent_size
            display_mode: Display mode (COMPACT, STANDARD, VERBOSE)
            use_emojis: Use emojis to improve readability
            humanize_keys: Transform technical keys into readable text
        """
        self.remove_private_keys = remove_private_keys
        self.remove_empty_values = remove_empty_values
        self.max_string_length = max_string_length
        self.max_array_items = max_array_items
        self.indent_size = indent_size
        self.display_mode = display_mode if isinstance(display_mode, DisplayMode) else DisplayMode.STANDARD
        self.use_emojis = use_emojis
        self.humanize_keys = humanize_keys
    
    def _is_empty_value(self, value: Any) -> bool:
        """Determines whether a value is considered blank"""
        if value is None:
            return True
        if isinstance(value, (str, list, dict)) and len(value) == 0:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False
    
    def _should_skip_key(self, key: str) -> bool:
        """Determines whether a key should be skipped"""
        if self.remove_private_keys and key.startswith('_'):
            return True
        return False
    
    def _humanize_key(self, key: str) -> str:
        """Transforms snake_case or camelCase into readable text"""
        if not self.humanize_keys:
            return key
        
        # Handles camelCase by inserting spaces before capital letters
        key = re.sub('([a-z])([A-Z])', r'\1 \2', key)
        
        # Replace underscores and hyphens with spaces
        key = key.replace('_', ' ').replace('-', ' ')
        
        # Capitalize each word
        words = key.split()
        
        # Handle common acronyms
        acronyms = ['ID', 'API', 'URL', 'HTTP', 'JSON', 'XML', 'UUID', 'IP']
        capitalized = []
        for word in words:
            if word.upper() in acronyms:
                capitalized.append(word.upper())
            else:
                capitalized.append(word.capitalize())
        
        return ' '.join(capitalized)
    
    def _detect_and_format_date(self, value: str) -> Optional[str]:
        """Detects and formats ISO dates"""
        # Pattern for ISO dates (2024-01-15T10:30:00Z or 2024-01-15)
        iso_pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$'
        
        if re.match(iso_pattern, value):
            try:
                # Replace 'Z' with '+00:00' for compatibility
                date_str = value.replace('Z', '+00:00')
                dt = datetime.fromisoformat(date_str)
                
                # Format according to precision
                if 'T' in value:
                    emoji = '📅' if self.use_emojis else ''
                    return f"{emoji} {dt.strftime('%d/%m/%Y à %H:%M')}".strip()
                else:
                    emoji = '📅' if self.use_emojis else ''
                    return f"{emoji} {dt.strftime('%d/%m/%Y')}".strip()
            except:
                pass
        
        return None
    
    def _get_status_emoji(self, value: Any) -> str:
        """Retourne un emoji selon le statut"""
        if not self.use_emojis:
            return ""
        
        status_map = {
            'active': '🟢',
            'inactive': '⚫',
            'disabled': '⚫',
            'pending': '🟡',
            'waiting': '🟡',
            'error': '🔴',
            'failed': '❌',
            'failure': '❌',
            'success': '✅',
            'succeeded': '✅',
            'completed': '✅',
            'running': '🔄',
            'processing': '⚙️',
            'warning': '⚠️',
            'info': 'ℹ️',
            'draft': '📝',
            'published': '🌐',
            'archived': '📦',
            'deleted': '🗑️',
            'true': '✓',
            'false': '✗',
        }
        
        value_str = str(value).lower()
        return status_map.get(value_str, '')
    
    def _smart_format_value(self, key: str, value: Any) -> str:
        """Formate intelligemment selon le type de données"""
        key_lower = key.lower()
        
        # Gestion des None
        if value is None:
            return "null"
        
        # Booléens
        if isinstance(value, bool):
            if self.display_mode == DisplayMode.VERBOSE:
                emoji = self._get_status_emoji(value)
                return f"{emoji} {'Oui' if value else 'Non'}".strip()
            emoji = self._get_status_emoji(value)
            return f"{emoji} {str(value).lower()}".strip()
        
        # Strings
        if isinstance(value, str):
            # Dates
            formatted_date = self._detect_and_format_date(value)
            if formatted_date:
                return formatted_date
            
            # URLs
            if value.startswith(('http://', 'https://')):
                emoji = '🔗' if self.use_emojis else ''
                truncated = self._truncate_string(value)
                return f"{emoji} {truncated}".strip()
            
            # Emails
            if '@' in value and '.' in value.split('@')[-1]:
                emoji = '📧' if self.use_emojis else ''
                return f"{emoji} {value}".strip()
            
            # Status/State (detection in the key)
            if any(word in key_lower for word in ['status', 'state', 'type', 'mode']):
                emoji = self._get_status_emoji(value)
                return f"{emoji} {value}".strip()
            
            # String normal
            cleaned = re.sub(r'\s+', ' ', value.strip())
            return f'"{self._truncate_string(cleaned)}"'
        
        # Numbers
        if isinstance(value, int):
            # Detection of context for numbers
            if any(word in key_lower for word in ['count', 'total', 'number', 'quantity', 'amount']):
                if self.display_mode == DisplayMode.VERBOSE:
                    return f"{value:,}".replace(',', ' ') + " item(s)"
                return f"{value:,}".replace(',', ' ')
            
            # Large numbers with separators
            if value > 1000:
                return f"{value:,}".replace(',', ' ')
            
            return str(value)
        
        if isinstance(value, float):
            # Price/Amounts
            if any(word in key_lower for word in ['price', 'amount', 'cost', 'total']):
                emoji = '💰' if self.use_emojis else ''
                return f"{emoji} {value:.2f}".strip()
            return f"{value:.2f}"
        
        return str(value)
    
    def _truncate_string(self, text: str) -> str:
        """Truncates a string if it is too long"""
        if len(text) <= self.max_string_length:
            return text
        return f"{text[:self.max_string_length]}... ({len(text)} characters)"
    
    def _create_summary(self, data: Dict) -> str:
        """Creates a summary of a line for complex objects"""
        # Search for common key fields to identify the object
        summary_fields = ['name', 'title', 'label', 'id', 'email', 'username', 'key']
        
        for field in summary_fields:
            if field in data:
                value = data[field]
                return f"({field}: {value})"
        
        # Otherwise, count the properties
        return f"({len(data)} property(s))"
    
    def process_json(self, data: Any) -> Any:
        """Clean and simplify a JSON recursively"""
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if self._should_skip_key(k):
                    continue
                
                processed_value = self.process_json(v)
                
                if self.remove_empty_values and self._is_empty_value(processed_value):
                    continue
                
                cleaned[k] = processed_value
            return cleaned
        
        elif isinstance(data, list):
            cleaned_list = []
            for item in data:
                processed_item = self.process_json(item)
                if not (self.remove_empty_values and self._is_empty_value(processed_item)):
                    cleaned_list.append(processed_item)
            return cleaned_list
        
        return data
    
    def flatten_dict(self, d: Dict, level: int = 0) -> List[str]:
        """Flattens a dictionary with formatting according to the display mode"""
        lines = []
        indent = ' ' * (self.indent_size * level)
        bullet = '•' if self.display_mode != DisplayMode.COMPACT and level == 0 else ''
        
        for k, v in d.items():
            human_key = self._humanize_key(k)
            key_display = f"{bullet} {human_key}" if bullet else human_key
            
            if isinstance(v, dict):
                if len(v) == 0:
                    lines.append(f"{indent}{key_display}: {{}}")
                else:
                    summary = self._create_summary(v) if self.display_mode != DisplayMode.COMPACT else ""
                    lines.append(f"{indent}{key_display}: {summary}".rstrip())
                    
                    if self.display_mode == DisplayMode.VERBOSE or len(v) <= 3:
                        lines.extend(self.flatten_dict(v, level + 1))
                    else:
                        lines.append(f"{indent}  ")
            
            elif isinstance(v, list):
                if len(v) == 0:
                    lines.append(f"{indent}{key_display}: []")
                else:
                    display_items = v[:self.max_array_items]
                    truncated = len(v) > self.max_array_items
                    
                    count_display = f"[{len(v)} item(s)]" if self.display_mode != DisplayMode.COMPACT else f"[{len(v)}]"
                    lines.append(f"{indent}{key_display}: {count_display}")
                    
                    for i, item in enumerate(display_items):
                        if isinstance(item, dict):
                            summary = self._create_summary(item)
                            lines.append(f"{indent}  [{i}] {summary}")
                            if self.display_mode == DisplayMode.VERBOSE:
                                lines.extend(self.flatten_dict(item, level + 2))
                        else:
                            formatted_item = self._smart_format_value(k, item)
                            lines.append(f"{indent}  [{i}]: {formatted_item}")
                    
                    if truncated:
                        remaining = len(v) - self.max_array_items
                        lines.append(f"{indent}  ... and {remaining} other element(s)")
            
            else:
                formatted_value = self._smart_format_value(k, v)
                lines.append(f"{indent}{key_display}: {formatted_value}")
        
        return lines
    
    def json_to_flat_text(self, data: Any) -> str:
        """Transforms JSON data into readable flat text"""
        if data is None:
            return "null"
        
        cleaned_data = self.process_json(data)
        
        if isinstance(cleaned_data, dict):
            if len(cleaned_data) == 0:
                return "{}"
            
            lines = []
            
            # Header for standard/verbose mode
            if self.display_mode != DisplayMode.COMPACT:
                obj_type = cleaned_data.get('type', cleaned_data.get('object', 'Objet'))
                emoji = '📋' if self.use_emojis else ''
                lines.append(f"{emoji} {obj_type.capitalize()}".strip())
                lines.append("")
            
            lines.extend(self.flatten_dict(cleaned_data))
            return '\n'.join(lines)
        
        elif isinstance(cleaned_data, list):
            if len(cleaned_data) == 0:
                return "[]"
            
            lines = []
            emoji = '📊' if self.use_emojis else ''
            lines.append(f"{emoji} array with {len(cleaned_data)} Item(s)".strip())
            
            for i, item in enumerate(cleaned_data[:self.max_array_items]):
                if isinstance(item, dict):
                    summary = self._create_summary(item)
                    lines.append(f"  [{i}] {summary}")
                    if self.display_mode == DisplayMode.VERBOSE or (self.display_mode == DisplayMode.STANDARD and i < 3):
                        lines.extend(self.flatten_dict(item, 2))
                else:
                    formatted_item = self._smart_format_value('item', item)
                    lines.append(f"  [{i}]: {formatted_item}")
            
            if len(cleaned_data) > self.max_array_items:
                remaining = len(cleaned_data) - self.max_array_items
                lines.append(f"  ... and {remaining} other element(s))")
            
            return '\n'.join(lines)
        
        else:
            return self._smart_format_value('value', cleaned_data)
    
    def analyze_structure(self, data: Any) -> str:
        """Provides an analysis of the JSON structure"""
        def count_elements(obj, counts=None):
            if counts is None:
                counts = {
                    'dicts': 0, 
                    'arrays': 0, 
                    'strings': 0, 
                    'numbers': 0, 
                    'bools': 0, 
                    'nulls': 0,
                    'max_depth': 0
                }
            
            if isinstance(obj, dict):
                counts['dicts'] += 1
                for v in obj.values():
                    count_elements(v, counts)
            elif isinstance(obj, list):
                counts['arrays'] += 1
                for item in obj:
                    count_elements(item, counts)
            elif isinstance(obj, str):
                counts['strings'] += 1
            elif isinstance(obj, (int, float)):
                counts['numbers'] += 1
            elif isinstance(obj, bool):
                counts['bools'] += 1
            elif obj is None:
                counts['nulls'] += 1
            
            return counts
        
        counts = count_elements(data)
        
        emoji = '📊' if self.use_emojis else ''
        analysis = [f"{emoji} structure analysis".strip(), ""]
        
        type_emojis = {
            'dicts': '📦',
            'arrays': '📋',
            'strings': '📝',
            'numbers': '🔢',
            'bools': '✓',
            'nulls': '∅'
        }
        
        for type_name, count in counts.items():
            if type_name == 'max_depth':
                continue
            if count > 0:
                emoji = type_emojis.get(type_name, '') if self.use_emojis else ''
                label = type_name.capitalize()
                analysis.append(f"{emoji} {label}: {count}".strip())
        
        return '\n'.join(analysis)


#Convenience functions with different modes

def process_json(data):
    """Simplified version for compatibility"""
    cleaner = JSONCleaner()
    return cleaner.process_json(data)

def json_to_flat_text(data, mode='standard'):
    """Simplified version with mode selection"""
    mode_map = {
        'compact': DisplayMode.COMPACT,
        'standard': DisplayMode.STANDARD,
        'verbose': DisplayMode.VERBOSE
    }
    cleaner = JSONCleaner(display_mode=mode_map.get(mode, DisplayMode.STANDARD))
    return cleaner.json_to_flat_text(data)

def json_to_compact(data):
    """Compact and technical format"""
    cleaner = JSONCleaner(
        display_mode=DisplayMode.COMPACT,
        use_emojis=False,
        humanize_keys=False
    )
    return cleaner.json_to_flat_text(data)

def json_to_standard(data):
    """Standard format with smart formatting"""
    cleaner = JSONCleaner(display_mode=DisplayMode.STANDARD)
    return cleaner.json_to_flat_text(data)

def json_to_verbose(data):
    """Verbose format with detailed information"""
    cleaner = JSONCleaner(
        display_mode=DisplayMode.VERBOSE,
        max_array_items=20
    )
    return cleaner.json_to_flat_text(data)
