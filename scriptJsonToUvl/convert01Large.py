import json
import re
from collections import deque

class SchemaProcessor:
    def __init__(self, definitions):
        self.definitions = definitions
        self.resolved_references = {}
        self.seen_references = set()
        self.processed_features = set()
        self.constraints = []  # Lista para almacenar las dependencias como constraints
        
        # Inicializamos un diccionario para almacenar descripciones por grupo
        self.descriptions = {
            'values': [],
            'restrictions': [],
            'dependencies': []
        }
        self.seen_descriptions = set()

        # Patrones para clasificar descripciones
        self.patterns = {
            'values': re.compile(r'(valid|values are|supported|acceptable|can be)', re.IGNORECASE),
            'restrictions': re.compile(r'(allowed|conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed)', re.IGNORECASE),
            'dependencies': re.compile(r'(depends on|requires|if[\s\S]*?only if|relies on|contingent upon|related to)', re.IGNORECASE)
        }

    def sanitize_name(self, name):
        """Replace non-alphanumeric characters with underscores and ensure uniqueness."""
        return name.replace("-", "_").replace(".", "_").replace("$", "")

    def resolve_reference(self, ref):
        """Resolve a reference to its actual schema."""
        if ref in self.resolved_references:
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/')
        schema = self.definitions
        for part in parts:
            schema = schema.get(part, {})
            if not schema:
                print(f"Warning: No se pudo resolver la siguiente referencia: {ref}")
                return None

        self.resolved_references[ref] = schema
        return schema

    def is_valid_description(self, description):
        """Check if the description is valid (not too short and not repetitive)."""
        if len(description) < 10:
            return False
        if description in self.seen_descriptions:
            return False
        self.seen_descriptions.add(description)
        return True

    def categorize_description(self, description, feature_name):
        """Categorize the description according to the patterns."""
        if not self.is_valid_description(description):
            return False

        for category, pattern in self.patterns.items():
            if pattern.search(description):
                self.descriptions[category].append((feature_name, description))
                return True
        
        return False

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

                if feature_type_data in ['array', 'object']:
                    feature_type_data = 'Boolean'
                elif feature_type_data == 'number':
                    feature_type_data = 'Integer'

                description = details.get('description', '')
                if description:
                    # Categorizar la descripción
                    self.categorize_description(description, full_name)

                feature = {
                    'name': full_name,
                    'type': feature_type,
                    'description': description,
                    'sub_features': [],
                    'type_data': feature_type_data
                }

                # Process references
                if '$ref' in details:
                    ref = details['$ref']
                    if ref not in self.seen_references:
                        self.seen_references.add(ref)
                        ref_schema = self.resolve_reference(ref)
                        if ref_schema:
                            ref_name = self.sanitize_name(ref.split('/')[-1])
                            # Generar constraint
                            self.constraints.append(f"{full_name} => {ref_name}")
                            if 'properties' in ref_schema:
                                sub_properties = ref_schema['properties']
                                sub_required = ref_schema.get('required', [])
                                sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                                feature['sub_features'].extend(sub_mandatory + sub_optional)
                            else:
                                # Si no hay 'properties', procesarlo como un tipo simple
                                feature_type_data = ref_schema.get('type', 'Boolean').capitalize()

                                """if feature_type_data in ['array', 'Object', 'String']:
                                    feature_type_data = 'Boolean'
                                elif feature_type_data == 'number':
                                    feature_type_data = 'Integer'
                                """
                                # Determinar si la referencia es 'mandatory' u 'optional'
                                feature_type = 'mandatory' if prop in current_required else 'optional'
                                
                                # Agregar la referencia procesada como un tipo simple
                                feature['sub_features'].append({
                                    'name': ref_name,
                                    'type': feature_type,
                                    'description': ref_schema.get('description', ''),
                                    'sub_features': [],
                                    'type_data': 'Boolean' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                                })
                                #print(f"Warning: Could not process reference: {ref}") # Descomentando la linea se pueden ver las estructuras simples que no tienen 'properties'
                        #else:
                            #print(f"Warning: Could not process reference: {ref}")
                
                # Process items in arrays
                elif feature['type_data'] == 'Boolean' and 'items' in details:
                    items = details['items']
                    if '$ref' in items:
                        ref = items['$ref']
                        if ref not in self.seen_references:
                            self.seen_references.add(ref)
                            ref_schema = self.resolve_reference(ref)
                            if ref_schema:
                                ref_name = self.sanitize_name(ref.split('/')[-1])
                                # Generar constraint
                                self.constraints.append(f"{full_name} => {ref_name}")
                                if ref_schema and 'properties' in ref_schema:
                                    item_mandatory, item_optional = self.parse_properties(ref_schema['properties'], [], full_name, current_depth + 1)
                                    feature['sub_features'].extend(item_mandatory + item_optional)
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

                # Process nested properties
                if 'properties' in details:
                    sub_properties = details['properties']
                    sub_required = details.get('required', [])
                    sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1)
                    feature['sub_features'].extend(sub_mandatory + sub_optional)

                if feature_type == 'mandatory':
                    mandatory_features.append(feature)
                else:
                    optional_features.append(feature)

                self.processed_features.add(full_name)

        return mandatory_features, optional_features

    def save_descriptions(self, file_path):
        """Save the collected descriptions to a JSON file."""
        print(f"Saving descriptions to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
        print("Descriptions saved successfully.")
        
    def save_constraints(self, file_path):
        """Save the collected constraints to a UVL file."""
        print(f"Saving constraints to {file_path}...")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("\nconstraints\n")
            for constraint in self.constraints:
                f.write(f"\t{constraint}\n")
        print("Constraints saved successfully.")

def load_json_file(file_path):
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def properties_to_uvl(feature_list, indent=1):
    """Convert feature list to UVL format."""
    uvl_output = ""
    indent_str = '\t' * indent
    for feature in feature_list:
        type_str = f"{feature['type_data'].capitalize()} " if feature['type_data'] else "Boolean "
        if feature['sub_features']:
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"  # {type_str} opcional si se necesita
            # uvl_output += f"{indent_str}\t{feature['type']}\n" opcional si se necesita

            # Separar características obligatorias y opcionales
            sub_mandatory = [f for f in feature['sub_features'] if f['type'] == 'mandatory']
            sub_optional = [f for f in feature['sub_features'] if f['type'] == 'optional']

            if sub_mandatory:
                uvl_output += f"{indent_str}\tmandatory\n"
                uvl_output += properties_to_uvl(sub_mandatory, indent + 2)
            if sub_optional:
                uvl_output += f"{indent_str}\toptional\n"
                uvl_output += properties_to_uvl(sub_optional, indent + 2)
        else:
            uvl_output += f"{indent_str}{type_str}{feature['name']} {{abstract}}\n"  # {type_str} opcional si se necesita
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):
    """Generate UVL from definitions and save descriptions."""
    definitions = load_json_file(definitions_file)
    processor = SchemaProcessor(definitions)
    uvl_output = "namespace KubernetesTest1\n\nfeatures\n\tKubernetes\n\t\toptional\n"

    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        required = schema.get('required', [])
        type_str_feature = 'Boolean' ## Por defecto al no tener definido un tipo los features principales se les pone como Boolean
        #print(f"Processing schema: {schema_name}")
        mandatory_features, optional_features = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name))

        if mandatory_features:
            uvl_output += f"\t\t\t{type_str_feature+' '}{processor.sanitize_name(schema_name)}\n" # {type_str_feature+' '}
            uvl_output += f"\t\t\t\tmandatory\n"
            uvl_output += properties_to_uvl(mandatory_features, indent=5)

            if optional_features:
                uvl_output += f"\t\t\t\toptional\n"
                uvl_output += properties_to_uvl(optional_features, indent=5)
        elif optional_features:
            uvl_output += f"\t\t\t{type_str_feature+' '}{processor.sanitize_name(schema_name)}\n" # {type_str_feature+' '}
            uvl_output += f"\t\t\t\toptional\n"
            uvl_output += properties_to_uvl(optional_features, indent=5)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)
    print(f"UVL output saved to {output_file}")

    # Save descriptions
    processor.save_descriptions(descriptions_file)
    
    # Save constraints
    processor.save_constraints(output_file)

# Rutas de archivo
definitions_file = 'C:/projects/investigacion/kubernetes-json-v1.30.2/v1.30.2/_definitions.json'
output_file = 'C:/projects/investigacion/scriptJsonToUvl/kubernetes_combined_01.uvl'
descriptions_file = 'C:/projects/investigacion/scriptJsonToUvl/descriptions_01.json'

# Generar archivo UVL y guardar descripciones
generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)
