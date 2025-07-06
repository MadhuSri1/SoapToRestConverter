import os
import argparse
import shutil
import glob
import xml.etree.ElementTree as ET

# --- Utility Functions ---
def parse_wsdl(wsdl_path):
    """Parse WSDL file and extract service and operation info."""
    tree = ET.parse(wsdl_path)
    root = tree.getroot()
    # Namespaces for WSDL
    ns = {'wsdl': 'http://schemas.xmlsoap.org/wsdl/'}
    services = []
    soap_endpoints = []
    # Add SOAP namespace for address
    ns_soap = {'soap': 'http://schemas.xmlsoap.org/wsdl/soap/'}
    for service in root.findall('wsdl:service', ns):
        service_name = service.attrib.get('name')
        ports = []
        for port in service.findall('wsdl:port', ns):
            port_name = port.attrib.get('name')
            ports.append(port_name)
            # Find soap:address
            address = port.find('soap:address', ns_soap)
            if address is not None:
                location = address.attrib.get('location')
                if location:
                    soap_endpoints.append({'service': service_name, 'port': port_name, 'location': location})
        services.append({'name': service_name, 'ports': ports})
    # Extract operations
    operations = []
    for portType in root.findall('wsdl:portType', ns):
        for op in portType.findall('wsdl:operation', ns):
            operations.append(op.attrib.get('name'))
    # Also extract messages for POJO generation
    messages = []
    for msg in root.findall('wsdl:message', ns):
        msg_name = msg.attrib.get('name')
        parts = []
        for part in msg.findall('wsdl:part', ns):
            part_name = part.attrib.get('name')
            part_type = part.attrib.get('type', 'string')
            parts.append({'name': part_name, 'type': part_type})
        messages.append({'name': msg_name, 'parts': parts})
    return services, operations, soap_endpoints, messages
def java_type_from_xsd(xsd_type):
    # Simple mapping for demo purposes
    if xsd_type.endswith(':string'):
        return 'String'
    if xsd_type.endswith(':int') or xsd_type.endswith(':integer'):
        return 'int'
    if xsd_type.endswith(':boolean'):
        return 'boolean'
    if xsd_type.endswith(':float') or xsd_type.endswith(':double'):
        return 'double'
    return 'String'  # default fallback

def generate_pojos(output_path, messages):
    pojo_dir = os.path.join(output_path, 'pojos')
    os.makedirs(pojo_dir, exist_ok=True)
    for msg in messages:
        class_name = msg['name'][0].upper() + msg['name'][1:]  # Capitalize
        file_path = os.path.join(pojo_dir, f'{class_name}.java')
        with open(file_path, 'w') as f:
            f.write(f'public class {class_name} ' + '{\n')
            # Fields
            for part in msg['parts']:
                java_type = java_type_from_xsd(part['type'])
                f.write(f'    private {java_type} {part["name"]};\n')
            f.write('\n')
            # Getters and setters
            for part in msg['parts']:
                java_type = java_type_from_xsd(part['type'])
                field = part['name']
                cap_field = field[0].upper() + field[1:]
                # Getter
                f.write(f'    public {java_type} get{cap_field}() ' + '{ return this.' + field + '; }\n')
                # Setter
                f.write(f'    public void set{cap_field}({java_type} {field}) ' + '{ this.' + field + ' = ' + field + '; }\n')
            f.write('}\n')

def scan_business_logic(project_path, language):
    """Scan for business logic files (Java or Python)."""
    if language == 'java':
        return glob.glob(os.path.join(project_path, '**', '*.java'), recursive=True)
    else:
        return glob.glob(os.path.join(project_path, '**', '*.py'), recursive=True)

def generate_rest_scaffold(target_language, output_path, services, operations, soap_endpoints):
    """Generate REST API scaffold in the target language, mapping SOAP endpoints to REST."""
    os.makedirs(output_path, exist_ok=True)
    # Use the first SOAP endpoint as the base for annotation (or none if not found)
    soap_ep_url = soap_endpoints[0]['location'] if soap_endpoints else '[SOAP endpoint URL not found]'
    if target_language == 'python':
        app_py = os.path.join(output_path, 'app.py')
        with open(app_py, 'w') as f:
            f.write('''from flask import Flask, request, jsonify\nimport requests\napp = Flask(__name__)\n\n''')
            f.write('# Example: If your SOAP project used a SOAP client, replace with REST calls using requests.post()\n')
            for op in operations:
                f.write(f"""# SOAP endpoint: {soap_ep_url}\n# SOAP operation: {op}\n@app.route('/{op}', methods=['POST'])\ndef {op}():\n    # Example REST call (replace URL and payload as needed)\n    # response = requests.post('http://rest-service/endpoint', json=request.json)\n    # return jsonify(response.json())\n    # TODO: Implement logic for SOAP operation '{op}' here\n    # You may parse request.json and return the appropriate response\n    return jsonify({{'message': '{op} endpoint'}})\n\n""")
            f.write("if __name__ == '__main__':\n    app.run(debug=True)\n")
    elif target_language == 'java':
        controller_path = os.path.join(output_path, 'SoapRestController.java')
        with open(controller_path, 'w') as f:
            f.write('''import org.springframework.web.bind.annotation.*;\nimport org.springframework.web.client.RestTemplate;\nimport org.springframework.beans.factory.annotation.Autowired;\n\n@RestController\npublic class SoapRestController {\n\n    // Example: If your SOAP project used WebServiceTemplate, use RestTemplate for REST calls\n    @Autowired\n    private RestTemplate restTemplate;\n\n''')
            for op in operations:
                f.write(f"""    // SOAP endpoint: {soap_ep_url}\n    // SOAP operation: {op}\n    @PostMapping("/{op}")\n    public String {op}(@RequestBody String requestBody) {{\n        // Example REST call (replace URL and payload as needed)\n        // String response = restTemplate.postForObject("http://rest-service/endpoint", requestBody, String.class);\n        // return response;\n        // TODO: Implement logic for SOAP operation '{op}' here\n        return "{op} endpoint";\n    }}\n\n""")
            f.write('}\n')
        # Also generate a configuration file for RestTemplate bean
        config_path = os.path.join(output_path, 'RestTemplateConfig.java')
        with open(config_path, 'w') as f:
            f.write('''import org.springframework.context.annotation.Bean;\nimport org.springframework.context.annotation.Configuration;\nimport org.springframework.web.client.RestTemplate;\n\n@Configuration\npublic class RestTemplateConfig {\n    @Bean\n    public RestTemplate restTemplate() {\n        return new RestTemplate();\n    }\n}\n''')

def main():
    parser = argparse.ArgumentParser(description='Convert SOAP project to REST project.')
    parser.add_argument('--soap_project', required=True, help='Path to the SOAP project directory')
    parser.add_argument('--wsdl', required=True, help='Path to the WSDL file')
    parser.add_argument('--target_language', choices=['python', 'java'], required=True, help='Target REST project language')
    parser.add_argument('--output', required=True, help='Output directory for REST project')
    args = parser.parse_args()


    print('Parsing WSDL...')
    services, operations, soap_endpoints, messages = parse_wsdl(args.wsdl)
    print(f'Found services: {services}')
    print(f'Found operations: {operations}')
    print(f'Found SOAP endpoints: {soap_endpoints}')

    print('Scanning for business logic files...')
    # Guess source language
    if glob.glob(os.path.join(args.soap_project, '**', '*.java'), recursive=True):
        source_language = 'java'
    else:
        source_language = 'python'
    logic_files = scan_business_logic(args.soap_project, source_language)
    print(f'Found business logic files: {logic_files}')

    print('Generating REST API scaffold...')
    generate_rest_scaffold(args.target_language, args.output, services, operations, soap_endpoints)
    print(f'REST API scaffold generated at {args.output}')
    # Generate POJOs if Java target
    if args.target_language == 'java':
        print('Generating POJOs from WSDL messages...')
        generate_pojos(args.output, messages)
        print(f'POJOs generated in {os.path.join(args.output, "pojos")}')

    # Output mapping template
    mapping_path = os.path.join(args.output, 'BUSINESS_LOGIC_MAPPING.txt')
    with open(mapping_path, 'w') as f:
        f.write("SOAP to REST Endpoint Mapping\n==============================\n\n")
        if soap_endpoints:
            f.write("SOAP Endpoints and their mapped REST endpoints:\n\n")
            for ep in soap_endpoints:
                for op in operations:
                    rest_url = f"/" + op
                    f.write(f"SOAP: {ep['location']} (service: {ep['service']}, port: {ep['port']})\n")
                    f.write(f"  -> REST: {rest_url} (method: POST)\n\n")
        else:
            f.write("No SOAP endpoints found in WSDL.\n\n")
        f.write("Map the following SOAP operations to REST endpoints manually as needed:\n\n")
        for op in operations:
            f.write(f"- {op}: Implement logic from corresponding SOAP method.\n")
        f.write('\nRefer to the following business logic files for reference:\n')
        for lf in logic_files:
            f.write(f"- {lf}\n")

        f.write("\n==============================\n")
        f.write("Manual Steps for the User:\n")
        f.write("------------------------------\n")
        f.write("1. Review the generated REST API scaffold (app.py for Python, SoapRestController.java for Java).\n")
        f.write("2. For each REST endpoint, copy or adapt the business logic from the corresponding SOAP method (see the business logic files listed above).\n")
        f.write("3. Update input/output handling: REST uses JSON, so parse request bodies and return JSON responses as needed.\n")
        if args.target_language == 'java':
            f.write("4. Review the generated POJOs in the 'pojos' directory. Use them as request/response bodies in your REST endpoints.\n")
            f.write("5. Replace any usage of WebServiceTemplate with RestTemplate for REST calls.\n")
            f.write("6. Register the RestTemplate bean (see RestTemplateConfig.java).\n")
        elif args.target_language == 'python':
            f.write("4. Replace any SOAP client code with requests.post() or similar for REST calls.\n")
        f.write("7. Test your new REST endpoints thoroughly.\n")
        f.write("8. Remove or refactor any SOAP-specific code that is no longer needed.\n")
        f.write("\n==============================\n")
    print(f'Mapping template generated at {mapping_path}')

if __name__ == '__main__':
    main()
