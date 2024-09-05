import json
import re
from collections import deque


class SchemaProcessor:
    def __init__(self, definitions):
        """
        Inicializa la clase `SchemaProcessor` para procesar y extraer información de las definiciones de un esquema JSON.
        descripciones, patrones y restricciones.

        Este constructor configura la clase con las definiciones del esquema JSON y establece varias variables internas
        que se utilizan para manejar referencias, descripciones, patrones y restricciones.
        
        definitions (dict): Un diccionario que contiene las definiciones del esquema JSON.

        
        """
        self.definitions = definitions # Un diccionario que organiza las descripciones en tres categorías:
        self.resolved_references = {}
        self.seen_references = set()
        self.processed_features = set()
        self.constraints = []  # Lista para almacenar las dependencias como constraints
        
        # Se inicializa un diccionario para almacenar descripciones por grupo
        self.descriptions = {
            'values': [], 
            'restrictions': [],
            'dependencies': []

        }
        self.seen_descriptions = set()

        # Patrones para clasificar descripciones en categorías de valores, restricciones y dependencias
        self.patterns = {
            'values': re.compile(r'(valid|values are|supported|acceptable|can be)', re.IGNORECASE),
            'restrictions': re.compile(r'(allowed|conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed)', re.IGNORECASE),
            'dependencies': re.compile(r'(depends on|requires|if[\s\S]*?only if|relies on|contingent upon|related to)', re.IGNORECASE)
        }

    def sanitize_name(self, name):
        """Reemplaza caracteres no permitidos en el nombre con guiones bajos y asegura que solo haya uno con ese nombre"""
        return name.replace("-", "_").replace(".", "_").replace("$", "")

    def resolve_reference(self, ref):
        """Resuelve una referencia a su esquema real dentro de las definiciones."""
        if ref in self.resolved_references:
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/')
        schema = self.definitions
        for part in parts:
            schema = schema.get(part, {})
            if not schema:
                print(f"Warning: No se pudo resolver la siguiente referencia: {ref}") # Se puede usar para comprobar si hay alguna referencia que se pierde y no se procesa
                return None

        self.resolved_references[ref] = schema
        return schema

    def is_valid_description(self, description):
        """Verifica si una descripción es válida (No muy corta y sin repeticiones) para analizarla después en busca de restricciones"""
        if len(description) < 10:
            return False
        if description in self.seen_descriptions:
            return False
        self.seen_descriptions.add(description)
        return True

    def is_required_based_on_description(self, description):
        """Determina si una propiedad es obligatoria basándose en si aparece Required al final de su descripción"""
        return description.strip().endswith("Required.")

    def extract_values(self, description):
        """Extrae valores que están entre comillas u otros delimitadores, solo si se encuentran ciertas palabras clave"""
        if not any(keyword in description.lower() for keyword in ['values are', 'possible values are']):
            return None
        
        value_patterns = [
            re.compile(r'(?<=Valid values are:)[\s\S]*?(?=\.)'),
            re.compile(r'(?<=Possible values are:)[\s\S]*?(?=\.)'),
            re.compile(r'["\'](.*?)["\']'),  # Captura valores entre comillas simples o dobles
        ]

        values = []
        add_quotes = False  # Variable para verificar si se necesita añadir comillas
        for pattern in value_patterns:
            matches = pattern.findall(description)
            for match in matches:
                split_values = re.split(r',\s*|\n', match)
                for v in split_values:
                    v = v.strip()
                    # Reemplazar '*' por "estrella"
                    v = v.replace('*', 'estrella')
                    # Filtrar valores que contienen puntos, corchetes, llaves o que son demasiado largos
                    if v and len(v) <= 15 and not any(char in v for char in {'.', '{', '}', '[', ']', ':'}):
                        values.append(v)
                        if ' ' in v:  # Si un valor contiene un espacio
                            add_quotes = True

        values = set(values)  # Eliminar duplicados
        if not values:
            return None
        return values, add_quotes  # Devuelve los valores y el nombre del feature


    def categorize_description(self, description, feature_name, type_data):
        """Categoriza la descripción según los patrones predefinidos."""
        
        if not self.is_valid_description(description):
            return False
        # Entrada de descripción con datos del tipo para mejorar la precisión de las reglas
        description_entry = {
        "feature_name": feature_name,
        "description": description,
        "type_data": type_data # Adición tipo para tener el tipo de dato para las restricciones
    }

        for category, pattern in self.patterns.items():
            if pattern.search(description):
                #self.descriptions[category].append((feature_name, description))
                self.descriptions[category].append((description_entry))
                return True
        
        return False

    def parse_properties(self, properties, required, parent_name="", depth=0):
        """
        Analiza las propiedades del esquema JSON y las clasifica en características obligatorias y opcionales.

        Este método recorre las propiedades de un esquema JSON, identifica si son obligatorias 
        u opcionales, y maneja las referencias y subpropiedades de manera recursiva.

        Args:
            properties (dict): Un diccionario que contiene las propiedades del esquema JSON.
            required (list): Una lista de nombres de propiedades que son obligatorias.
            parent_name (str): El nombre de la propiedad padre, usado para construir nombres completos.
            depth (int): El nivel de profundidad actual en el esquema, usado para la recursión.

        Returns:
            mandatory_features, optional_features: Dos listas de los grupos principales, la primera contiene características obligatorias y la segunda características opcionales.
        """
        mandatory_features = []
        optional_features = []
        queue = deque([(properties, required, parent_name, depth)])
        #numValores = 0
        while queue:
            current_properties, current_required, current_parent, current_depth = queue.popleft()
            for prop, details in current_properties.items():
                sanitized_name = self.sanitize_name(prop)
                full_name = f"{current_parent}_{sanitized_name}" if current_parent else sanitized_name
                
                if full_name in self.processed_features:
                    continue
                # Verificar si la propiedad es requerida basado en su descripción
                description = details.get('description', '')
                is_required_by_description = self.is_required_based_on_description(description)

                #feature_type = 'mandatory' if prop in current_required else 'optional'
                feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional' # Variante para usar los Required de las descripciones
                feature_type_data = details.get('type', 'Boolean')

                if feature_type_data in ['array', 'object']:
                    feature_type_data = 'Boolean'
                elif feature_type_data == 'number':
                    feature_type_data = 'Integer'

                #description = details.get('description', '')
                if description:
                    # Categorizar la descripción
                    self.categorize_description(description, full_name, feature_type_data)

                feature = {
                    'name': full_name,
                    'type': feature_type,
                    'description': description,
                    'sub_features': [],
                    'type_data': feature_type_data
                }

                # Procesar referencias
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
                
                # Procesar ítems en arreglos
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
                        items_type_data = items.get('type', 'Boolean') ## Modificacion para que los items simples tengan tipo de datos tambien
                        
                        if feature_type_data in ['array', 'object']:
                            feature_type_data = 'Boolean'
                        elif feature_type_data == 'number':
                            feature_type_data = 'Integer'

                        feature['sub_features'].append({
                            'name': f"{full_name}_items",
                            'type': item_type,
                            'description': 'Items in the array',
                            'sub_features': [],
                            'type_data': items_type_data
                        })
                # Extraer y añadir valores como subfeatures
                extracted_values = self.extract_values(description)

                if extracted_values:
                    values, add_quotes = extracted_values
                    for value in values:
                        print("Los valores del feature son:"+value)
                        #combined_feature = f'"{full_name}_{value}"' if add_quotes else f"{full_name}_{value}"
                        #print(f"Los nombres del feature son:{combined_feature}")

                        feature['sub_features'].append({
                            'name': f'"{full_name}_{value}"' if add_quotes else f"{full_name}_{value}", #f"{full_name}_{self.sanitize_name(combined_feature)}"
                            'type': 'alternative',  # Los valores obtenidos se tratan como alternativos
                            'description': f"Specific value: {value}",
                            'sub_features': [],
                            'type_data': "String" # Definir si obtener el tipo de dato o por defecto String
                        })
                        #numValores += 1
                #print(f"Valores obtenidos: {numValores}")

                # Procesar propiedades anidadas
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
        """
        Guarda las descripciones recopiladas en un archivo JSON.

        Este método escribe las descripciones almacenadas en `self.descriptions` a un archivo JSON 
        especificado por `file_path`.

        Args:
            file_path (str): La ruta del archivo JSON donde se guardarán las descripciones.
        """
        print(f"Saving descriptions to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
        print("Descriptions saved successfully.")

    def save_constraints(self, file_path):
        """
        Guarda las restricciones recopiladas en un archivo UVL.

        Este método escribe las restricciones almacenadas en `self.constraints` a un archivo UVL 
        especificado por `file_path`.

        Args:
            file_path (str): La ruta del archivo UVL donde se guardarán las restricciones.
        """
        print(f"Saving constraints to {file_path}...")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("\nconstraints\n" + "//Restricciones obtenidas de las referencias:\n")
            for constraint in self.constraints:
                f.write(f"\t{constraint}\n")
        print("Constraints saved successfully.")

def load_json_file(file_path):
    """
    Carga un archivo JSON.

    Este método lee el contenido de un archivo JSON especificado por `file_path` y lo devuelve 
    como un objeto de Python.

    Args:
        file_path (str): La ruta del archivo JSON que se cargará.

    Returns:
        dict: El contenido del archivo JSON como un diccionario de Python.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def properties_to_uvl(feature_list, indent=1):
    """
    Convierte una lista de características a formato UVL.

    Este método recorre cada característica en la lista proporcionada y la convierte en una línea
    de texto UVL, gestionando adecuadamente la indentación y la jerarquía de subcaracterísticas.

    Args:
        feature_list (list): Lista de características a convertir.
        indent (int): El nivel de indentación actual para la conversión.

    Returns:
        str: La salida en formato UVL como una cadena de texto.
    """
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
            sub_alternative = [f for f in feature['sub_features'] if f['type'] == 'alternative']

            if sub_mandatory:
                uvl_output += f"{indent_str}\tmandatory\n"
                uvl_output += properties_to_uvl(sub_mandatory, indent + 2)
            if sub_optional:
                uvl_output += f"{indent_str}\toptional\n"
                uvl_output += properties_to_uvl(sub_optional, indent + 2)
            if sub_alternative:
                uvl_output += f"{indent_str}\talternative\n"
                uvl_output += properties_to_uvl(sub_alternative, indent + 2)
        else:
            uvl_output += f"{indent_str}{type_str}{feature['name']} {{abstract}}\n"  # {type_str} opcional si se necesita
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):
    """
    Genera un archivo UVL a partir de las definiciones de un esquema JSON y guarda las descripciones y restricciones.

    Este método carga un archivo de definiciones JSON, procesa las propiedades del esquema y genera un archivo UVL (Universal 
    Variability Language). El archivo UVL contiene una representación jerárquica de las características definidas en el esquema JSON.
    Además, guarda las descripciones de las características y las restricciones extraídas del esquema en archivos separados.

    Args:
        definitions_file (str): La ruta al archivo JSON que contiene las definiciones del esquema.
        output_file (str): La ruta donde se guardará el archivo UVL generado.
        descriptions_file (str): La ruta donde se guardarán las descripciones extraídas en formato JSON.

        El resultado es un archivo UVL que representa las características del esquema JSON, junto con archivos adicionales que documentan 
        las descripciones y las restricciones encontradas.
    
    """
    definitions = load_json_file(definitions_file) # Cargar el archivo de definiciones JSON
    processor = SchemaProcessor(definitions) # Inicializar el procesador de esquemas con las definiciones cargadas
    uvl_output = "namespace KubernetesTest1\n\nfeatures\n\tKubernetes\n\t\toptional\n" # Iniciar la estructura base del archivo UVL

    # Procesar cada definición en el archivo JSON
    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        required = schema.get('required', [])
        type_str_feature = 'Boolean' ## Por defecto al no tener definido un tipo los features principales se les pone como Boolean
        #print(f"Processing schema: {schema_name}")
        mandatory_features, optional_features = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name)) # Obtener características obligatorias y opcionales
        
        # Agregar las características obligatorias y opcionales al archivo UVL
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

    # Guardar el archivo UVL generado
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)
    print(f"UVL output saved to {output_file}")

    # Guardar las descripciones extraídas
    processor.save_descriptions(descriptions_file)
    
    # Guardar las restricciones en el archivo UVL
    processor.save_constraints(output_file)

# Rutas de archivo relativas
#definitions_file = '../kubernetes-json-schema/v1.30.4/_definitions.json'
definitions_file = '../kubernetes-json-v1.30.2/v1.30.2/_definitions.json'
output_file = './kubernetes_combined_01.uvl'
descriptions_file = './descriptions_01.json'

# Generar archivo UVL y guardar descripciones
generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)
