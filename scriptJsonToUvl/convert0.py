import json
from collections import deque

class SchemaProcessor:
    def __init__(self, definitions):
        self.definitions = definitions
        self.resolved_references = {}
        self.processed_features = {}
        self.seen_references = set()
        self.descriptions = {}

    # Función para cambiar y eliminar los carácteres no válidos en el formato uvl
    def sanitize_name(self, name):
        """Replace non-alphanumeric characters with underscores and ensure uniqueness."""
        return name.replace("-", "_").replace(".", "_").replace("$", "")
    
    # Función que resuelve una referencia JSON y devuelve el esquema al que se hace referencia
    def resolve_reference(self, ref):
        if ref in self.resolved_references:
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/')
        schema = self.definitions
        for part in parts:
            schema = schema.get(part, {})
            if not schema:
                return None

        self.resolved_references[ref] = schema
        return schema
    
    # Función que mapea las propiedades
    def parse_properties(self, properties, required, parent_name="", depth=0):
        mandatory_features = []
        optional_features = []
        queue = deque([(properties, required, parent_name, depth)])

        while queue:
            current_properties, current_required, current_parent, current_depth = queue.popleft()
            for prop, details in current_properties.items():
                sanitized_name = self.sanitize_name(prop)
                full_name = f"{current_parent}_{sanitized_name}" if current_parent else sanitized_name

                if full_name in self.processed_features:
                    continue

                feature_type = 'mandatory' if prop in current_required else 'optional'
                feature_type_data = details.get('type', 'Boolean')

                if feature_type_data == 'array' or feature_type_data == 'object':
                    feature_type_data = 'Boolean'
                elif feature_type_data == 'number':
                    feature_type_data = 'Integer'

                feature = {
                    'name': full_name,
                    'type': feature_type,
                    'description': details.get('description', ''),
                    'sub_features': [],
                    'type_data': feature_type_data
                }

                if feature['description']:
                    self.descriptions[full_name] = feature['description']

                if '$ref' in details:
                    if details['$ref'] in self.seen_references:
                        continue
                    self.seen_references.add(details['$ref'])
                    ref_schema = self.resolve_reference(details['$ref'])
                    if ref_schema and 'properties' in ref_schema:
                        sub_properties = ref_schema['properties']
                        sub_required = ref_schema.get('required', [])
                        sub_features = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                        feature['sub_features'].extend(sub_features)

                elif feature['type_data'] == 'Boolean' and 'items' in details:
                    items = details['items']
                    if '$ref' in items:
                        if items['$ref'] in self.seen_references:
                            continue
                        self.seen_references.add(items['$ref'])
                        ref_schema = self.resolve_reference(items['$ref'])
                        if ref_schema and 'properties' in ref_schema:
                            item_properties = self.parse_properties(ref_schema['properties'], [], full_name, current_depth + 1)
                            feature['sub_features'].extend(item_properties)
                    else:
                        item_required = items.get('required', [])
                        item_type = 'mandatory' if full_name in item_required else 'optional'
                        feature['sub_features'].append({
                            'name': f"{full_name}_items",
                            'type': item_type,
                            'description': 'Items in the array',
                            'sub_features': [],
                            'type_data': 'Boolean'
                        })

                if 'properties' in details:
                    sub_properties = details['properties']
                    sub_required = details.get('required', [])
                    sub_features = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                    feature['sub_features'].extend(sub_features)

                if feature_type == 'mandatory':
                    mandatory_features.append(feature)
                else:
                    optional_features.append(feature)

                self.processed_features[full_name] = feature

        combined_features = []
        if mandatory_features:
            combined_features.extend(mandatory_features)
        if optional_features:
            combined_features.extend(optional_features)

        return combined_features

    def save_descriptions(self, file_path):
        """Save the collected descriptions to a JSON file."""
        print(f"Saving descriptions to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
        print("Descriptions saved successfully.")

# Se carga el archivo json con el permiso de lectura y se usa la codificación utf-8
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
# Se define la conversión de las propiedades a uvl
def properties_to_uvl(feature_list, indent=1):
    uvl_output = ""
    indent_str = '\t' * indent
    for feature in feature_list:
        type_str = f"{feature['type_data'].capitalize()} " if feature['type_data'] else "Boolean "
        if feature['sub_features']:
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"
            if feature['type'] == 'mandatory':
                uvl_output += f"{indent_str}\tmandatory\n"
            if feature['type'] == 'optional':
                uvl_output += f"{indent_str}\toptional\n"
            uvl_output += properties_to_uvl(feature['sub_features'], indent + 1)
        else:
            uvl_output += f"{indent_str}{type_str}{feature['name']} {{abstract}}\n"
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):
    definitions = load_json_file(definitions_file)
    processor = SchemaProcessor(definitions)
    uvl_output = "namespace KubernetesTest1\n\nfeatures\n\tKubernetes\n\t\toptional\n"
    
    # Se procesan las definiciones completas de los esquemas como features en Kubernetes
    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        required = schema.get('required', [])
        print(f"Processing schema: {schema_name}")
        feature_list = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name), depth=1)

        uvl_output += properties_to_uvl([{
            'name': processor.sanitize_name(schema_name),
            'type': 'mandatory' if required else 'optional',
            'description': '',
            'sub_features': feature_list,
            'type_data': 'Boolean'
        }], indent=2)  # Ajuste de indentación

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)

    # Guardar las descripciones
    processor.save_descriptions(descriptions_file)

    print(f"UVL file saved as {output_file}")
    print(f"Descriptions file saved as {descriptions_file}")

# Rutas de archivo
definitions_file = 'C:/projects/investigacion/kubernetes-json-v1.30.2/v1.30.2/_definitions.json'
output_file = 'C:/projects/investigacion/scriptJsonToUvl/kubernetes_combined.uvl'
descriptions_file = 'C:/projects/investigacion/scriptJsonToUvl/descriptions.json'

generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)