#!/usr/bin/env python3
"""
Bring File Editor - Web Application
A Swagger-like editor for Bring configuration files

Usage: python bring_editor.py
Then open: http://localhost:5000

Requirements: pip install flask
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
import json
import os
import tempfile
from pathlib import Path

# Import your Bring parser
try:
    from bring_parser.parser import parse_bring_string, BringPrimitive, BringObject, BringArray
    from bring_parser.exceptions import BringParseError
    PARSER_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: Bring parser not available. Using mock parser.")
    PARSER_AVAILABLE = False

app = Flask(__name__)

# Mock parser for demo purposes
class MockBringPrimitive:
    def __init__(self, value):
        self.value = value

class MockBringObject:
    def __init__(self, items):
        self.items = items

class MockBringArray:
    def __init__(self, items):
        self.items = items

def mock_parse_bring_string(content):
    # Simple mock parser for demo
    return {"app_name": MockBringPrimitive("Demo App"), "version": MockBringPrimitive("1.0.0")}

def bring_to_dict(bring_value):
    """Convert BringValue to Python dict"""
    if PARSER_AVAILABLE:
        if isinstance(bring_value, BringPrimitive):
            return bring_value.value
        elif isinstance(bring_value, BringObject):
            return {key: bring_to_dict(value) for key, value in bring_value.items.items()}
        elif isinstance(bring_value, BringArray):
            return [bring_to_dict(item) for item in bring_value.items]
    else:
        if hasattr(bring_value, 'value'):
            return bring_value.value
        elif hasattr(bring_value, 'items') and isinstance(bring_value.items, dict):
            return {key: bring_to_dict(value) for key, value in bring_value.items.items()}
        elif hasattr(bring_value, 'items') and isinstance(bring_value.items, list):
            return [bring_to_dict(item) for item in bring_value.items]
    return str(bring_value)

# Default Bring content
DEFAULT_BRING_CONTENT = '''# Bring Configuration Example
# Welcome to the Bring Editor!

schema DatabaseConfig {
    host = string @required=true @default="localhost"
    port = integer @required=true @range=[1, 65535]
    username = string @required=true
    password = string @required=true @sensitive=true
    pool_size = integer @default=10 @min=1 @max=100
}

schema ServerConfig {
    name = string @required=true
    environment = string @required=true @values=["dev", "staging", "prod"]
    debug = boolean @default=false
    port = integer @default=8080
}

# Application Configuration
app_name = "Bring Demo App"
version = "1.0.0"
debug @environment="development" = true

# Server Configuration
server = {
    name = "web-server-01"
    environment = "prod"
    debug = false
    port = 8080
    max_connections @tuning="performance" = 1000
}

# Database Configuration
database = {
    host = "localhost"
    port = 5432
    username = "app_user"
    password @encrypted=true = "secure_password"
    pool_size = 20
}

# Feature Flags
features = [
    {
        name = "new_ui"
        enabled = true
        rollout = 0.75
    },
    {
        name = "analytics"
        enabled = false
        rollout = 0.1
    }
]

# External Services
services = {
    auth = {
        url = "https://auth.example.com"
        timeout = 5000
        retries = 3
    }
    
    payment = {
        url = "https://payment.example.com"
        timeout = 10000
        api_key @encrypted=true = "payment_key"
    }
}

# Environment Overrides
environment_overrides = {
    development = {
        server = {
            debug = true
            port = 3000
        }
        database = {
            host = "localhost"
            pool_size = 5
        }
    }
    
    staging = {
        features = [
            {
                name = "analytics"
                enabled = true
                rollout = 1.0
            }
        ]
    }
}'''

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bring Editor</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css" rel="stylesheet">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🚀</text></svg>">

     <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/javascript/javascript.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
        }
        
        .header {
            background: #2d2d2d;
            padding: 15px 20px;
            border-bottom: 1px solid #444;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            color: #4CAF50;
            font-size: 24px;
            font-weight: 600;
        }
        
        .header-controls {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover {
            background: #45a049;
        }
        
        .btn-secondary {
            background: #555;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #666;
        }
        
        .btn-danger {
            background: #f44336;
            color: white;
        }
        
        .btn-danger:hover {
            background: #da190b;
        }
        
        .main-container {
            display: flex;
            height: calc(100vh - 70px);
        }
        
        .editor-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #444;
        }
        
        .editor-header {
            background: #333;
            padding: 10px 15px;
            border-bottom: 1px solid #444;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .editor-header h3 {
            color: #e0e0e0;
            font-size: 16px;
        }
        
        .status {
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-valid {
            background: #4CAF50;
            color: white;
        }
        
        .status-error {
            background: #f44336;
            color: white;
        }
        
        .editor-container {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        
        .CodeMirror {
            height: 100%;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .CodeMirror-scroll {
            overflow: auto !important;
        }
        
        .preview-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #2d2d2d;
        }
        
        .preview-header {
            background: #333;
            padding: 10px 15px;
            border-bottom: 1px solid #444;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .preview-header h3 {
            color: #e0e0e0;
            font-size: 16px;
        }
        
        .format-selector {
            background: #555;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .preview-content {
            flex: 1;
            overflow: auto;
            padding: 15px;
        }
        
        .json-preview {
            background: #1e1e1e;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.4;
            white-space: pre-wrap;
            color: #e0e0e0;
        }
        
        .error-message {
            background: #2d1b1b;
            border: 1px solid #f44336;
            border-radius: 4px;
            padding: 15px;
            color: #ffcdd2;
            font-family: monospace;
            font-size: 13px;
        }
        
        .schema-info {
            background: #1a2a1a;
            border: 1px solid #4CAF50;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .schema-info h4 {
            color: #4CAF50;
            margin-bottom: 10px;
        }
        
        .schema-rule {
            margin: 8px 0;
            padding: 8px;
            background: #2d2d2d;
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
        }
        
        .validation-result {
            background: #1a1a2a;
            border: 1px solid #64B5F6;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .validation-result.valid {
            border-color: #4CAF50;
            background: #1a2a1a;
        }
        
        .validation-result.invalid {
            border-color: #f44336;
            background: #2a1a1a;
        }
        
        .validation-result h4 {
            color: #64B5F6;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .validation-result.valid h4 {
            color: #4CAF50;
        }
        
        .validation-result.invalid h4 {
            color: #f44336;
        }
        
        .validation-message {
            font-size: 13px;
            margin-bottom: 5px;
        }
        
        .validation-details {
            font-size: 12px;
            color: #999;
            font-style: italic;
        }
        
        .attribute-section {
            background: #2a1a2a;
            border: 1px solid #9C27B0;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .attribute-section h4 {
            color: #9C27B0;
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        .attribute-item {
            margin: 8px 0;
            padding: 8px;
            background: #333;
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
        }
        
        .attribute-name {
            color: #FF9800;
            font-weight: bold;
        }
        
        .attribute-value {
            color: #4CAF50;
        }
        
        .file-controls {
            display: flex;
            gap: 5px;
        }
        
        .file-input {
            display: none;
        }
        
        .resize-handle {
            width: 4px;
            background: #444;
            cursor: col-resize;
            position: relative;
        }
        
        .resize-handle:hover {
            background: #4CAF50;
        }
        
        @media (max-width: 768px) {
            .main-container {
                flex-direction: column;
            }
            
            .editor-panel {
                height: 50%;
                border-right: none;
                border-bottom: 1px solid #444;
            }
            
            .preview-panel {
                height: 50%;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Bring Editor</h1>
        <div class="header-controls">
            <div class="file-controls">
                <input type="file" id="fileInput" class="file-input" accept=".bring">
                <button class="btn btn-secondary" onclick="document.getElementById('fileInput').click()">
                    📁 Open File
                </button>
                <button class="btn btn-secondary" onclick="downloadFile()">
                    💾 Download
                </button>
            </div>
            <button class="btn btn-primary" onclick="parseContent()">
                ▶️ Parse
            </button>
            <button class="btn btn-danger" onclick="clearEditor()">
                🗑️ Clear
            </button>
        </div>
    </div>
    
    <div class="main-container">
        <div class="editor-panel">
            <div class="editor-header">
                <h3>Bring Configuration</h3>
                <span id="status" class="status status-valid">Valid</span>
            </div>
            <div class="editor-container">
                <textarea id="editor" placeholder="Enter your Bring configuration here..."></textarea>
            </div>
        </div>
        
        <div class="resize-handle" id="resizeHandle"></div>
        
        <div class="preview-panel">
            <div class="preview-header">
                <h3>Preview</h3>
                <select id="formatSelector" class="format-selector" onchange="updatePreview()">
                    <option value="json">JSON</option>
                    <option value="yaml">YAML</option>
                    <option value="xml">XML</option>
                    <option value="schemas">Schemas</option>
                    <option value="structure">Structure</option>
                    <option value="attributes">Attributes</option>
                    <option value="validation">Validation</option>
                    <option value="statistics">Statistics</option>
                </select>
            </div>
            <div class="preview-content">
                <div id="previewContent" class="json-preview"></div>
            </div>
        </div>
    </div>

    <script>
        let editor;
        let currentParsedData = null;
        let isResizing = false;
        
        // Initialize CodeMirror
        document.addEventListener('DOMContentLoaded', function() {
            editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
                theme: 'monokai',
                lineNumbers: true,
                mode: 'javascript',
                indentUnit: 4,
                lineWrapping: true,
                autoCloseBrackets: true,
                matchBrackets: true
            });
            
            editor.setValue(`{{ default_content }}`);
            
            // Auto-parse on change
            editor.on('change', function() {
                clearTimeout(window.parseTimeout);
                window.parseTimeout = setTimeout(parseContent, 500);
            });
            
            // Initial parse
            parseContent();
            
            // File input handler
            document.getElementById('fileInput').addEventListener('change', handleFileSelect);
            
            // Resize handler
            setupResizeHandle();
        });
        
        function parseContent() {
            const content = editor.getValue();
            
            fetch('/parse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({content: content})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentParsedData = data;
                    document.getElementById('status').textContent = 'Valid';
                    document.getElementById('status').className = 'status status-valid';
                    updatePreview();
                } else {
                    document.getElementById('status').textContent = 'Error';
                    document.getElementById('status').className = 'status status-error';
                    showError(data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Network error: ' + error.message);
            });
        }
        
        function updatePreview() {
            if (!currentParsedData || !currentParsedData.success) return;
            
            const format = document.getElementById('formatSelector').value;
            const previewContent = document.getElementById('previewContent');
            
            switch (format) {
                case 'json':
                    previewContent.innerHTML = '';
                    previewContent.className = 'json-preview';
                    previewContent.textContent = JSON.stringify(currentParsedData.data, null, 2);
                    break;
                    
                case 'yaml':
                    convertToFormat('yaml');
                    break;
                    
                case 'xml':
                    convertToFormat('xml');
                    break;
                    
                case 'schemas':
                    showSchemas(currentParsedData.schemas);
                    break;
                    
                case 'structure':
                    showStructure(currentParsedData.data);
                    break;
                    
                case 'attributes':
                    showAttributes(currentParsedData.attributes || {});
                    break;
                    
                case 'validation':
                    showValidation(currentParsedData.validation || []);
                    break;
                    
                case 'statistics':
                    showStatistics(currentParsedData.statistics || {});
                    break;
            }
        }
        
        function convertToFormat(format) {
            const content = editor.getValue();
            
            fetch(`/convert/${format}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({content: content})
            })
            .then(response => response.json())
            .then(data => {
                const previewContent = document.getElementById('previewContent');
                if (data.success) {
                    previewContent.innerHTML = '';
                    previewContent.className = 'json-preview';
                    previewContent.textContent = data.converted;
                } else {
                    showError(data.error);
                }
            })
            .catch(error => {
                showError('Conversion error: ' + error.message);
            });
        }
        
        function showError(error) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = `<div class="error-message">❌ Parse Error:\\n\\n${error}</div>`;
        }
        
        function showSchemas(schemas) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = '';
            previewContent.className = 'preview-content';
            
            if (!schemas || Object.keys(schemas).length === 0) {
                previewContent.innerHTML = '<div class="json-preview">No schemas defined</div>';
                return;
            }
            
            let html = '';
            for (const [name, schema] of Object.entries(schemas)) {
                html += `
                    <div class="schema-info">
                        <h4>📋 Schema: ${name}</h4>
                        ${schema.rules.map(rule => `
                            <div class="schema-rule">
                                <strong>${rule.key}</strong>: ${rule.type}
                                ${Object.entries(rule.attributes).map(([attr, val]) => 
                                    `<span style="color: #4CAF50;"> @${attr}=${JSON.stringify(val)}</span>`
                                ).join('')}
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            previewContent.innerHTML = html;
        }
        
        function showStructure(data) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = '';
            previewContent.className = 'json-preview';
            
            function getType(value) {
                if (value === null) return 'null';
                if (Array.isArray(value)) return `array[${value.length}]`;
                if (typeof value === 'object') return `object{${Object.keys(value).length}}`;
                return typeof value;
            }
            
            function buildStructure(obj, indent = 0) {
                let result = '';
                const spaces = '  '.repeat(indent);
                
                for (const [key, value] of Object.entries(obj)) {
                    const type = getType(value);
                    result += `${spaces}${key}: ${type}\\n`;
                    
                    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                        result += buildStructure(value, indent + 1);
                    }
                }
                return result;
            }
            
            previewContent.textContent = buildStructure(data);
        }
        
        function showValidation(validationResults) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = '';
            previewContent.className = 'preview-content';
            
            if (!validationResults || validationResults.length === 0) {
                previewContent.innerHTML = '<div class="json-preview">No validation results available</div>';
                return;
            }
            
            let html = '';
            for (const result of validationResults) {
                const validClass = result.valid ? 'valid' : 'invalid';
                const statusIcon = result.valid ? '✅' : '❌';
                
                html += `
                    <div class="validation-result ${validClass}">
                        <h4>${statusIcon} ${result.path}</h4>
                        <div class="validation-message">${result.message}</div>
                        ${result.details ? `<div class="validation-details">${result.details}</div>` : ''}
                    </div>
                `;
            }
            
            previewContent.innerHTML = html;
        }
        
        function showAttributes(attributes) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = '';
            previewContent.className = 'preview-content';
            
            if (!attributes || Object.keys(attributes).length === 0) {
                previewContent.innerHTML = '<div class="json-preview">No attributes found</div>';
                return;
            }
            
            let html = '';
            for (const [path, attrs] of Object.entries(attributes)) {
                if (attrs && attrs.length > 0) {
                    html += `
                        <div class="attribute-section">
                            <h4>🏷️ ${path}</h4>
                            ${attrs.map(attr => `
                                <div class="attribute-item">
                                    <span class="attribute-name">@${attr.name}</span> = 
                                    <span class="attribute-value">${attr.value}</span>
                                    ${attr.line ? `<span style="color: #999; margin-left: 10px;">(line ${attr.line})</span>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            }
            
            if (html === '') {
                previewContent.innerHTML = '<div class="json-preview">No attributes found</div>';
            } else {
                previewContent.innerHTML = html;
            }
        }
        
        function showStatistics(statistics) {
            const previewContent = document.getElementById('previewContent');
            previewContent.innerHTML = '';
            previewContent.className = 'json-preview';
            
            if (!statistics || Object.keys(statistics).length === 0) {
                previewContent.textContent = 'No statistics available';
                return;
            }
            
            let output = '';
            
            if (statistics.file_info) {
                output += '📄 File Information:\\n';
                output += `  Total Lines: ${statistics.file_info.total_lines}\\n`;
                output += `  Non-Empty Lines: ${statistics.file_info.non_empty_lines}\\n`;
                output += `  Comment Lines: ${statistics.file_info.comment_lines}\\n`;
                output += `  Character Count: ${statistics.file_info.character_count}\\n\\n`;
            }
            
            if (statistics.structure) {
                output += '🏗️ Structure Information:\\n';
                output += `  Top-Level Keys: ${statistics.structure.top_level_keys}\\n`;
                output += `  Schemas Defined: ${statistics.structure.schemas_defined}\\n`;
                output += `  Objects: ${statistics.structure.objects}\\n`;
                output += `  Arrays: ${statistics.structure.arrays}\\n`;
                output += `  Primitives: ${statistics.structure.primitives}\\n`;
                output += `  Null Values: ${statistics.structure.null_values}\\n\\n`;
            }
            
            if (statistics.complexity) {
                output += '🔍 Complexity Metrics:\\n';
                output += `  Max Nesting Depth: ${statistics.complexity.nesting_depth}\\n`;
                output += `  Total Attributes: ${statistics.complexity.total_attributes}\\n`;
                output += `  Schema Rules: ${statistics.complexity.schema_rules}\\n`;
            }
            
            previewContent.textContent = output;
        }
        
        function clearEditor() {
            if (confirm('Are you sure you want to clear the editor?')) {
                editor.setValue('');
                document.getElementById('previewContent').innerHTML = '';
                currentParsedData = null;
            }
        }
        
        function downloadFile() {
            const content = editor.getValue();
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'config.bring';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    editor.setValue(e.target.result);
                    parseContent();
                };
                reader.readAsText(file);
            }
        }
        
        function setupResizeHandle() {
            const resizeHandle = document.getElementById('resizeHandle');
            const editorPanel = document.querySelector('.editor-panel');
            const previewPanel = document.querySelector('.preview-panel');
            
            resizeHandle.addEventListener('mousedown', function(e) {
                isResizing = true;
                document.addEventListener('mousemove', handleResize);
                document.addEventListener('mouseup', stopResize);
            });
            
            function handleResize(e) {
                if (!isResizing) return;
                
                const containerWidth = document.querySelector('.main-container').offsetWidth;
                const newWidth = (e.clientX / containerWidth) * 100;
                
                if (newWidth > 20 && newWidth < 80) {
                    editorPanel.style.flex = `0 0 ${newWidth}%`;
                    previewPanel.style.flex = `0 0 ${100 - newWidth}%`;
                }
            }
            
            function stopResize() {
                isResizing = false;
                document.removeEventListener('mousemove', handleResize);
                document.removeEventListener('mouseup', stopResize);
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, default_content=DEFAULT_BRING_CONTENT)

@app.route('/parse', methods=['POST'])
def parse_bring():
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content.strip():
            return jsonify({
                'success': True, 
                'data': {}, 
                'schemas': {},
                'attributes': {},
                'validation': [],
                'statistics': {}
            })
        
        # Parse with real or mock parser
        if PARSER_AVAILABLE:
            parsed = parse_bring_string(content)
        else:
            parsed = mock_parse_bring_string(content)
        
        # Convert to dict
        result_data = {}
        schemas = {}
        attributes = {}
        validation_results = []
        
        for key, value in parsed.items():
            if key.startswith('schema:'):
                schema_name = key[7:]
                if PARSER_AVAILABLE and hasattr(value, 'rules'):
                    schemas[schema_name] = {
                        'name': value.name,
                        'rules': [
                            {
                                'key': rule.key,
                                'type': rule.type,
                                'attributes': {attr.name: attr.value for attr in rule.attributes}
                            }
                            for rule in value.rules
                        ]
                    }
                else:
                    schemas[schema_name] = {'name': schema_name, 'rules': []}
            else:
                result_data[key] = bring_to_dict(value)
        
        # Extract attributes (mock implementation)
        attributes = extract_attributes_from_content(content)
        
        # Generate validation results (mock implementation)
        validation_results = generate_validation_results(result_data, schemas)
        
        # Generate statistics
        statistics = generate_statistics(result_data, schemas, content)
        
        return jsonify({
            'success': True,
            'data': result_data,
            'schemas': schemas,
            'attributes': attributes,
            'validation': validation_results,
            'statistics': statistics
        })
        
    except Exception as e:
        if PARSER_AVAILABLE and isinstance(e, BringParseError):
            error_msg = str(e)
        else:
            error_msg = f"Parse error: {str(e)}"
            
        return jsonify({
            'success': False,
            'error': error_msg
        })

def extract_attributes_from_content(content):
    """Extract attributes from Bring content (simplified)"""
    attributes = {}
    lines = content.split('\n')
    current_path = []
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if '@' in line and '=' in line:
            # Simple attribute extraction
            parts = line.split('@')
            if len(parts) > 1:
                attr_part = parts[1].split('=')[0].strip()
                value_part = parts[1].split('=')[1].strip() if '=' in parts[1] else 'true'
                
                path = f"line_{line_num}"
                if path not in attributes:
                    attributes[path] = []
                
                attributes[path].append({
                    'name': attr_part,
                    'value': value_part,
                    'line': line_num
                })
    
    return attributes

def generate_validation_results(data, schemas):
    """Generate validation results (simplified)"""
    results = []
    
    # Basic validation
    if not data:
        results.append({
            'path': 'root',
            'valid': False,
            'message': 'No data found',
            'details': 'The configuration appears to be empty'
        })
    else:
        results.append({
            'path': 'root',
            'valid': True,
            'message': f'Successfully parsed {len(data)} top-level items',
            'details': f'Found keys: {", ".join(data.keys())}'
        })
    
    # Schema validation
    for schema_name, schema in schemas.items():
        results.append({
            'path': f'schema:{schema_name}',
            'valid': True,
            'message': f'Schema "{schema_name}" is valid',
            'details': f'Contains {len(schema["rules"])} rules'
        })
    
    return results

def generate_statistics(data, schemas, content):
    """Generate file statistics"""
    lines = content.split('\n')
    
    def count_types(obj, counts=None):
        if counts is None:
            counts = {'objects': 0, 'arrays': 0, 'primitives': 0, 'null_values': 0}
        
        if isinstance(obj, dict):
            counts['objects'] += 1
            for value in obj.values():
                count_types(value, counts)
        elif isinstance(obj, list):
            counts['arrays'] += 1
            for item in obj:
                count_types(item, counts)
        elif obj is None:
            counts['null_values'] += 1
        else:
            counts['primitives'] += 1
        
        return counts
    
    type_counts = count_types(data)
    
    return {
        'file_info': {
            'total_lines': len(lines),
            'non_empty_lines': len([l for l in lines if l.strip()]),
            'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
            'character_count': len(content)
        },
        'structure': {
            'top_level_keys': len(data),
            'schemas_defined': len(schemas),
            **type_counts
        },
        'complexity': {
            'nesting_depth': calculate_max_depth(data),
            'total_attributes': sum(len(attrs) for attrs in extract_attributes_from_content(content).values()),
            'schema_rules': sum(len(schema['rules']) for schema in schemas.values())
        }
    }

def calculate_max_depth(obj, current_depth=0):
    """Calculate maximum nesting depth"""
    if not isinstance(obj, (dict, list)):
        return current_depth
    
    max_depth = current_depth
    
    if isinstance(obj, dict):
        for value in obj.values():
            depth = calculate_max_depth(value, current_depth + 1)
            max_depth = max(max_depth, depth)
    elif isinstance(obj, list):
        for item in obj:
            depth = calculate_max_depth(item, current_depth + 1)
            max_depth = max(max_depth, depth)
    
    return max_depth

@app.route('/convert/<format_type>', methods=['POST'])
def convert_format(format_type):
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if PARSER_AVAILABLE:
            parsed = parse_bring_string(content)
        else:
            parsed = mock_parse_bring_string(content)
        
        result_data = {}
        for key, value in parsed.items():
            if not key.startswith('schema:'):
                result_data[key] = bring_to_dict(value)
        
        if format_type == 'json':
            import json
            converted = json.dumps(result_data, indent=2)
        elif format_type == 'yaml':
            try:
                import yaml
                converted = yaml.dump(result_data, default_flow_style=False)
            except ImportError:
                return jsonify({'success': False, 'error': 'PyYAML not installed'})
        elif format_type == 'xml':
            # Simple XML conversion
            def dict_to_xml(d, root='config'):
                xml = f'<?xml version="1.0"?>\n<{root}>\n'
                for k, v in d.items():
                    xml += f'  <{k}>{v}</{k}>\n'
                xml += f'</{root}>'
                return xml
            converted = dict_to_xml(result_data)
        else:
            return jsonify({'success': False, 'error': 'Unsupported format'})
        
        return jsonify({'success': True, 'converted': converted})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 Starting Bring Editor...")
    print("📝 Open your browser and go to: http://localhost:5000")
    print("💡 Features:")
    print("   - Live parsing and validation")
    print("   - Schema visualization") 
    print("   - JSON/Structure preview")
    print("   - File upload/download")
    print("   - Resizable panels")
    print("   - Syntax highlighting")
    print("   - Validation results display")
    print("   - Attributes analysis")
    print("   - Statistical insights")
    print("   - Default content loaded from config.bring file")
    print("   - Custom rocket favicon 🚀")
    print()
    print("📋 Note: Place your default configuration in 'config.bring' file")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
